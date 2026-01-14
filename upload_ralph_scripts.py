#!/usr/bin/env python3
"""
Extract bash scripts from ralph-claude-code-multidb-prompt.md and upload to VPS
"""
import subprocess
import re

# Script extraction mapping: (start_line, end_line, filename)
SCRIPTS = [
    (45, 293, 'detect_databases.sh'),
    (300, 551, 'db_manager.sh'),
    (558, 624, 'sync_databases.sh'),
    (631, 652, 'notify_telegram.sh'),
    (659, 733, 'run_story.sh'),
    (740, 912, 'ralph_loop.sh'),
    (919, 954, 'check_status.sh'),
    (965, 992, '.env.template'),
    (998, 1084, 'README.md'),
]

def read_script_lines(filepath, start, end):
    """Read specific lines from file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        # Account for 1-indexed line numbers
        script_lines = lines[start-1:end]
        # Remove markdown code fence markers
        content = ''.join(script_lines)
        # Remove markdown bash/markdown markers
        content = re.sub(r'^```bash\n', '', content)
        content = re.sub(r'^```markdown\n', '', content)
        content = re.sub(r'\n```$', '', content)
        return content

def upload_script(content, remote_path, make_executable=False):
    """Upload script content to VPS via SSH"""
    # Escape single quotes in content for bash
    escaped_content = content.replace("'", "'\"'\"'")

    # Create file on VPS
    cmd = f"ssh root@72.60.175.144 'cat > {remote_path} << '\''ENDOFSCRIPT'\''\\n{content}\\nENDOFSCRIPT'\n"

    # Use a temp file approach instead
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.tmp', encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name

    try:
        # SCP the temp file to VPS
        scp_cmd = f'scp -o StrictHostKeyChecking=no "{temp_path}" root@72.60.175.144:{remote_path}'
        result = subprocess.run(scp_cmd, shell=True, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error uploading {remote_path}: {result.stderr}")
            return False

        # Make executable if needed
        if make_executable:
            chmod_cmd = f'ssh root@72.60.175.144 "chmod +x {remote_path}"'
            subprocess.run(chmod_cmd, shell=True)

        print(f"[OK] Uploaded: {remote_path}")
        return True

    finally:
        os.unlink(temp_path)

def main():
    source_file = 'ralph-claude-code-multidb-prompt.md'

    print("="*60)
    print("Ralph Scripts Upload Tool")
    print("="*60)
    print()

    success_count = 0

    for start, end, filename in SCRIPTS:
        print(f"Extracting {filename} (lines {start}-{end})...")

        try:
            content = read_script_lines(source_file, start, end)

            # Determine remote path
            if filename in ['.env.template', 'README.md']:
                if filename == '.env.template':
                    remote_path = '/root/ralph/config/.env.template'
                else:
                    remote_path = '/root/ralph/README.md'
                make_exec = False
            else:
                remote_path = f'/root/ralph/scripts/{filename}'
                make_exec = True

            # Upload
            if upload_script(content, remote_path, make_exec):
                success_count += 1

        except Exception as e:
            print(f"[ERROR] Error processing {filename}: {e}")

    print()
    print("="*60)
    print(f"Upload complete: {success_count}/{len(SCRIPTS)} files uploaded")
    print("="*60)
    print()
    print("Next steps:")
    print("1. ssh root@72.60.175.144")
    print("2. cd /root/ralph")
    print("3. ./scripts/detect_databases.sh")
    print("4. ./scripts/db_manager.sh status")

if __name__ == '__main__':
    main()
