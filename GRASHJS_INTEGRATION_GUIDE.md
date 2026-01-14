# Grashjs CMMS Integration Guide for Rivet-PRO

## Repository Information

- **Forked Repository**: `https://github.com/Mikecranesync/cmms`
- **Local Clone**: `C:\Users\hharp\OneDrive\Desktop\grashjs-cmms`
- **Original Repository**: `https://github.com/Grashjs/cmms`

## Architecture Overview

### Tech Stack
- **Backend**: Java 1.8 + Spring Boot 2.6.7 + JPA/Hibernate
- **Frontend**: React + TypeScript
- **Mobile**: React Native + Expo
- **Database**: PostgreSQL 16 with Liquibase migrations
- **File Storage**: MinIO (local) or Google Cloud Storage
- **Deployment**: Docker + Docker Compose
- **Authentication**: JWT + OAuth2 (Google/Microsoft SSO)

### Core Components

#### 1. Backend (api/)
```
api/src/main/java/com/grash/
├── model/              # JPA entities (Asset, WorkOrder, PreventiveMaintenance, Part, etc.)
├── repository/         # Spring Data JPA repositories
├── service/            # Business logic layer
├── controller/         # REST API endpoints
├── dto/               # Data Transfer Objects
├── mapper/            # MapStruct entity-DTO mappers
├── security/          # JWT, OAuth2, authentication
├── event/             # Application events
└── configuration/     # Spring configuration
```

#### 2. Database Schema (Liquibase)
```
api/src/main/resources/db/
├── master.xml                  # Main changelog orchestrator
└── changelog/                  # Migration files (173+ files)
    ├── liquibase-outputChangeLog.xml
    ├── liquibase-diffChangeLog.xml
    └── [timestamped migrations]
```

#### 3. Frontend (frontend/)
- React + TypeScript application
- Material-UI (MUI) components
- React Router for navigation
- API integration via axios/fetch

#### 4. Mobile (mobile/)
- React Native with Expo
- Connects to backend API
- Available on Google Play and App Store

## Key Data Models

### 1. Asset (Equipment)
```java
@Entity
public class Asset extends CompanyAudit {
    private String customId;
    private String name;
    private String description;
    private String serialNumber;
    private String model;
    private String manufacturer;
    private String barCode;
    private String nfcId;
    private String area;
    private Double acquisitionCost;
    private Date warrantyExpirationDate;
    private Date inServiceDate;
    private AssetStatus status;  // OPERATIONAL, DOWN, etc.

    @ManyToOne Location location;
    @ManyToOne Asset parentAsset;
    @ManyToOne AssetCategory category;
    @ManyToOne OwnUser primaryUser;
    @ManyToMany List<OwnUser> assignedTo;
    @ManyToMany List<Team> teams;
    @ManyToMany List<Vendor> vendors;
    @ManyToMany List<Part> parts;
    @ManyToMany List<File> files;
    @OneToOne File image;
    @OneToOne Deprecation deprecation;
}
```

### 2. WorkOrder
```java
@Entity
@Audited  // Hibernate Envers for history tracking
public class WorkOrder extends WorkOrderBase {
    private Long id;
    private String customId;
    private Status status;  // OPEN, IN_PROGRESS, ON_HOLD, COMPLETE
    private Date completedOn;
    private String feedback;
    private String signature;
    private boolean archived;

    @ManyToOne OwnUser completedBy;
    @ManyToOne Request parentRequest;
    @ManyToOne PreventiveMaintenance parentPreventiveMaintenance;
}
```

### 3. WorkOrderBase (Abstract)
```java
@MappedSuperclass
public abstract class WorkOrderBase extends CompanyAudit {
    private String title;
    private String description;
    private Priority priority;
    private Date dueDate;
    private double estimatedDuration;

    @ManyToOne Location location;
    @ManyToOne Asset asset;
    @ManyToOne OwnUser primaryUser;
    @ManyToMany List<OwnUser> assignedTo;
    @ManyToMany List<Team> teams;
    @ManyToMany List<File> files;
    @ManyToMany List<Task> tasks;  // Checklist items
}
```

### 4. PreventiveMaintenance
```java
@Entity
public class PreventiveMaintenance extends WorkOrderBase {
    private Long id;
    private String customId;
    private String name;

    @OneToOne(cascade = CascadeType.ALL)
    private Schedule schedule;  // Defines recurrence
}
```

### 5. Schedule
```java
@Entity
public class Schedule {
    private boolean startsOn;
    private Date startsOnDate;
    private boolean endsOn;
    private Date endsOnDate;
    private int frequency;  // Number of time units
    private ScheduleFrequency frequencyType;  // DAILY, WEEKLY, MONTHLY, YEARLY
    private List<Integer> daysOfWeek;  // 1=Monday, 7=Sunday
    private List<Integer> daysOfMonth;  // 1-31

    @OneToOne PreventiveMaintenance preventiveMaintenance;
}
```

### 6. Part (Inventory)
```java
@Entity
public class Part extends CompanyAudit {
    private String name;
    private String description;
    private String barcode;
    private double cost;
    private double quantity;
    private double minQuantity;  // Reorder threshold
    private String area;
    private boolean nonStock;

    @ManyToOne PartCategory category;
    @ManyToMany List<OwnUser> assignedTo;
    @ManyToMany List<Vendor> vendors;
    @ManyToMany List<Customer> customers;
    @ManyToMany List<PreventiveMaintenance> preventiveMaintenances;
    @ManyToMany List<File> files;
    @OneToOne File image;
}
```

### 7. Other Key Entities
- **Location**: Hierarchical location management with Google Maps integration
- **Labor**: Time tracking for work orders
- **Vendor**: Vendor management for parts and services
- **Customer**: Customer/client tracking
- **Team**: User groups for assignment
- **Request**: Service requests that can be converted to work orders
- **PurchaseOrder**: Parts procurement
- **Meter**: Asset meter readings (hours, miles, etc.)
- **File**: Attachment management (images, documents)
- **Notification**: User notifications

## Deployment Steps

### 1. Local Deployment (Docker)

```bash
cd C:\Users\hharp\OneDrive\Desktop\grashjs-cmms

# Ensure .env file is configured
# Review and update:
# - POSTGRES_USER / POSTGRES_PWD
# - MINIO_USER / MINIO_PASSWORD
# - JWT_SECRET_KEY
# - PUBLIC_FRONT_URL / PUBLIC_API_URL (if deploying remotely)

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f api
docker-compose logs -f frontend

# Access the application
# Frontend: http://localhost:3000
# API: http://localhost:8080
# MinIO Console: http://localhost:9001
```

### 2. Production Deployment

#### Option A: Deploy to Your Existing Server (72.60.175.144)

1. **Upload Grashjs to server**:
```bash
cd C:\Users\hharp\OneDrive\Desktop
scp -r grashjs-cmms root@72.60.175.144:/opt/

# Or use git clone directly on server
ssh root@72.60.175.144
cd /opt
git clone https://github.com/Mikecranesync/cmms.git grashjs-cmms
cd grashjs-cmms
```

2. **Configure .env for production**:
```bash
nano .env

# Update these variables:
PUBLIC_FRONT_URL=http://72.60.175.144:3000
PUBLIC_API_URL=http://72.60.175.144:8080
PUBLIC_MINIO_ENDPOINT=http://72.60.175.144:9000

# Or use domain if available:
# PUBLIC_FRONT_URL=https://cmms.yourdomain.com
# PUBLIC_API_URL=https://api.cmms.yourdomain.com
```

3. **Open firewall ports**:
```bash
# PostgreSQL (5432) - only if you need external access
# API (8080)
# Frontend (3000)
# MinIO (9000, 9001)

# Example with ufw:
ufw allow 3000/tcp
ufw allow 8080/tcp
ufw allow 9000/tcp
ufw allow 9001/tcp
```

4. **Deploy**:
```bash
docker-compose up -d
```

#### Option B: Deploy with Reverse Proxy (Recommended)

Use nginx or Caddy to proxy requests:

**Nginx example**:
```nginx
# /etc/nginx/sites-available/cmms

server {
    listen 80;
    server_name cmms.yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

server {
    listen 80;
    server_name api.cmms.yourdomain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Then use Certbot for SSL:
```bash
certbot --nginx -d cmms.yourdomain.com -d api.cmms.yourdomain.com
```

## Telegram Bot Integration Strategy

Since Grashjs CMMS is a Java/Spring Boot application with REST API, we need to create a bridge between Telegram and the Java backend.

### Option 1: Python Telegram Bot → Grashjs REST API

Keep your existing Python bot but point it to Grashjs API:

```python
# rivet_pro/bot/grashjs_client.py
import requests

class GrashjsClient:
    def __init__(self, api_url, username, password):
        self.api_url = api_url
        self.token = self.login(username, password)

    def login(self, username, password):
        response = requests.post(
            f"{self.api_url}/auth/login",
            json={"username": username, "password": password}
        )
        return response.json()["token"]

    def create_work_order(self, data):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{self.api_url}/work-orders",
            headers=headers,
            json=data
        )
        return response.json()

    def get_assets(self, search=None):
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"search": search} if search else {}
        response = requests.get(
            f"{self.api_url}/assets",
            headers=headers,
            params=params
        )
        return response.json()
```

### Option 2: Java Telegram Bot (Recommended for full integration)

Add Telegram Bot SDK to Grashjs:

```xml
<!-- pom.xml -->
<dependency>
    <groupId>org.telegram</groupId>
    <artifactId>telegrambots-spring-boot-starter</artifactId>
    <version>6.9.7.1</version>
</dependency>
```

Create Telegram bot service in Grashjs:

```java
// api/src/main/java/com/grash/telegram/TelegramBotService.java
@Component
public class TelegramBotService extends TelegramLongPollingBot {

    @Autowired
    private WorkOrderService workOrderService;

    @Autowired
    private AssetService assetService;

    @Override
    public void onUpdateReceived(Update update) {
        if (update.hasMessage() && update.getMessage().hasText()) {
            String text = update.getMessage().getText();
            Long chatId = update.getMessage().getChatId();

            if (text.startsWith("/wo")) {
                handleWorkOrder(chatId, text);
            } else if (text.startsWith("/equip")) {
                handleEquipment(chatId, text);
            }
        }
    }

    private void handleWorkOrder(Long chatId, String text) {
        // Create work order via WorkOrderService
        // Send response via sendMessage()
    }
}
```

### Option 3: Hybrid Approach (Recommended for Rivet-PRO)

Keep your existing Python bot infrastructure but use it as a thin client:

```python
# rivet_pro/bot/handlers/work_order.py
from telegram import Update
from telegram.ext import ContextTypes
from rivet_pro.integrations.grashjs_api import GrashjsAPI

async def create_work_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Parse user input
    title = context.args[0] if context.args else "Unnamed Work Order"

    # Call Grashjs API
    api = GrashjsAPI(base_url="http://localhost:8080")
    work_order = api.create_work_order({
        "title": title,
        "priority": "MEDIUM",
        "status": "OPEN",
        "createdBy": update.message.from_user.id
    })

    # Send confirmation
    await update.message.reply_text(
        f"✅ Work Order #{work_order['id']} created: {work_order['title']}"
    )
```

## Grashjs API Endpoints

Key REST endpoints available:

### Authentication
- `POST /auth/login` - Login with username/password
- `POST /auth/register` - Register new user
- `GET /auth/me` - Get current user info

### Work Orders
- `GET /work-orders` - List work orders (with filtering)
- `POST /work-orders` - Create work order
- `GET /work-orders/{id}` - Get work order details
- `PATCH /work-orders/{id}` - Update work order
- `DELETE /work-orders/{id}` - Delete work order
- `POST /work-orders/{id}/complete` - Mark as complete

### Assets (Equipment)
- `GET /assets` - List assets
- `POST /assets` - Create asset
- `GET /assets/{id}` - Get asset details
- `PATCH /assets/{id}` - Update asset
- `DELETE /assets/{id}` - Delete asset

### Preventive Maintenance
- `GET /preventive-maintenances` - List PM schedules
- `POST /preventive-maintenances` - Create PM schedule
- `GET /preventive-maintenances/{id}` - Get PM details
- `PATCH /preventive-maintenances/{id}` - Update PM
- `DELETE /preventive-maintenances/{id}` - Delete PM

### Parts & Inventory
- `GET /parts` - List parts
- `POST /parts` - Create part
- `GET /parts/{id}` - Get part details
- `PATCH /parts/{id}` - Update part (including quantity)
- `DELETE /parts/{id}` - Delete part

### Other Endpoints
- `/locations`, `/vendors`, `/customers`, `/teams`
- `/requests` - Service requests
- `/purchase-orders` - Purchase orders
- `/meters` - Meter readings
- `/files` - File uploads/downloads
- `/notifications` - User notifications
- `/analytics` - Reports and analytics

## Next Steps

1. **Deploy Grashjs locally first**:
   ```bash
   cd C:\Users\hharp\OneDrive\Desktop\grashjs-cmms
   docker-compose up -d
   ```
   Access at http://localhost:3000

2. **Create test account and explore**:
   - Register new account
   - Create sample assets, work orders, PM schedules
   - Understand the UI and workflows

3. **Test API integration**:
   - Get JWT token via `/auth/login`
   - Call API endpoints using Postman or curl
   - Verify data flow

4. **Choose integration strategy**:
   - Python bot → REST API (easiest, keep existing bot)
   - Java Telegram bot (full integration, requires Java skills)
   - Hybrid approach (recommended)

5. **Deploy to production**:
   - Upload to your server
   - Configure .env for production URLs
   - Set up reverse proxy + SSL
   - Open firewall ports
   - Test end-to-end

6. **Migrate existing data** (if you have data from Agent Factory):
   - Export from Agent Factory
   - Transform to Grashjs format
   - Import via API or direct SQL

## Integration with Rivet-PRO

To integrate with your existing Rivet-PRO structure:

```
Rivet-PRO/
├── bot/                    # Your existing Telegram bot
│   ├── orchestrator.py    # Keep this
│   └── integrations/
│       └── grashjs/       # NEW: Grashjs API client
│           ├── __init__.py
│           ├── client.py  # REST API wrapper
│           └── models.py  # Pydantic models
├── grashjs-cmms/          # Grashjs deployment (can be separate repo)
│   ├── api/               # Java backend
│   ├── frontend/          # React frontend
│   ├── docker-compose.yml
│   └── .env
└── docs/
    └── GRASHJS_API.md     # API documentation
```

## Resources

- **Grashjs Docs**: https://docs.atlas-cmms.com
- **Your Fork**: https://github.com/Mikecranesync/cmms
- **Demo Site**: https://atlas-cmms.com
- **Discord**: https://discord.gg/cHqyVRYpkA
- **API Docs**: Available at `http://localhost:8080/swagger-ui.html` (if Swagger is enabled)

## License

Grashjs CMMS is dual-licensed:
- **GPLv3** for open source use (free)
- **Commercial License** for white labeling, SSO, advanced features

For production use with custom branding, you may need to purchase a commercial license. Contact: contact@atlas-cmms.com
