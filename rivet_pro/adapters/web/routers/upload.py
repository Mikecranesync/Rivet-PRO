"""
Photo upload router for OCR analysis.
Allows web users to upload equipment nameplate photos for automatic OCR and equipment creation.
"""

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import Optional

from rivet_pro.adapters.web.dependencies import get_current_user, get_db, UserInDB
from rivet_pro.core.services import analyze_image
from rivet_pro.core.services.equipment_service import EquipmentService
from rivet_pro.infra.database import Database
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)

router = APIRouter()


class OCRResult(BaseModel):
    """OCR analysis result."""
    manufacturer: Optional[str]
    model_number: Optional[str]
    serial_number: Optional[str]
    component_type: Optional[str]
    confidence: float
    provider_used: Optional[str]


class UploadResponse(BaseModel):
    """Photo upload response."""
    ocr: OCRResult
    equipment: Optional[dict] = None
    is_new_equipment: bool = False


@router.post("/nameplate", response_model=UploadResponse)
async def upload_nameplate(
    file: UploadFile = File(...),
    create_equipment: bool = True,
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Upload equipment nameplate photo for OCR analysis.

    Automatically creates or matches equipment if create_equipment=True.

    Args:
        file: Image file (JPG, PNG, HEIC)
        create_equipment: Whether to auto-create equipment from OCR result
        current_user: Authenticated user
        db: Database connection

    Returns:
        OCR result and optionally created equipment
    """
    # Validate file type
    if file.content_type not in ["image/jpeg", "image/png", "image/heic", "image/jpg"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Supported: JPG, PNG, HEIC"
        )

    # Validate file size (20MB max)
    file_bytes = await file.read()
    file_size_mb = len(file_bytes) / (1024 * 1024)

    if file_size_mb > 20:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {file_size_mb:.1f}MB. Maximum: 20MB"
        )

    logger.info(
        f"Photo upload | user={current_user.email} | "
        f"filename={file.filename} | size={file_size_mb:.2f}MB"
    )

    try:
        # Run OCR analysis
        ocr_result = await analyze_image(
            image_bytes=file_bytes,
            user_id=str(current_user.id)
        )

        # Check for OCR errors
        if hasattr(ocr_result, 'error') and ocr_result.error:
            logger.warning(f"OCR error for user {current_user.email}: {ocr_result.error}")
            return UploadResponse(
                ocr=OCRResult(
                    manufacturer=None,
                    model_number=None,
                    serial_number=None,
                    component_type=None,
                    confidence=0.0,
                    provider_used=ocr_result.provider_used if hasattr(ocr_result, 'provider_used') else None
                ),
                equipment=None,
                is_new_equipment=False
            )

        # Create OCR response
        ocr_response = OCRResult(
            manufacturer=ocr_result.manufacturer,
            model_number=ocr_result.model_number,
            serial_number=ocr_result.serial_number,
            component_type=getattr(ocr_result, 'component_type', None),
            confidence=ocr_result.confidence,
            provider_used=ocr_result.provider_used if hasattr(ocr_result, 'provider_used') else None
        )

        # Auto-create equipment if requested and we have manufacturer
        equipment_data = None
        is_new = False

        if create_equipment and ocr_result.manufacturer:
            try:
                service = EquipmentService(db)

                equipment_id, equipment_number, is_new = await service.match_or_create_equipment(
                    manufacturer=ocr_result.manufacturer,
                    model_number=ocr_result.model_number,
                    serial_number=ocr_result.serial_number,
                    equipment_type=getattr(ocr_result, 'component_type', None),
                    location=None,  # Can be set later
                    user_id=str(current_user.id)
                )

                equipment_data = await service.get_equipment_by_id(equipment_id)

                logger.info(
                    f"Equipment {'created' if is_new else 'matched'} from OCR | "
                    f"equipment_number={equipment_number} | user={current_user.email}"
                )

            except Exception as e:
                logger.error(f"Failed to create equipment from OCR: {e}", exc_info=True)
                # Continue anyway - OCR succeeded even if equipment creation failed

        logger.info(
            f"OCR complete | user={current_user.email} | "
            f"manufacturer={ocr_result.manufacturer} | "
            f"confidence={ocr_result.confidence:.0%}"
        )

        return UploadResponse(
            ocr=ocr_response,
            equipment=equipment_data,
            is_new_equipment=is_new
        )

    except Exception as e:
        logger.error(f"Photo upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process image: {str(e)}"
        )
