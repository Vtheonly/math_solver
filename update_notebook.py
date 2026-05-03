import json
import sys

def update_nb(filename):
    try:
        with open(filename, "r") as f:
            nb = json.load(f)
    except:
        return
        
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            source = cell.get("source", [])
            
            # Check if this is Cell 2 (setup repo)
            if any("CELL 2: Clone repository" in line for line in source):
                new_source = []
                for line in source:
                    if "pip install -q pika" not in line and "Install pika" not in line:
                        new_source.append(line)
                cell["source"] = new_source
                
            # Check if this is Cell 6 (Worker)
            elif any("CELL 6: Start Async RabbitMQ Worker" in line or "Start Async HTTP Worker" in line for line in source):
                new_code = """# ============================================================
# CELL 6: Start Async HTTP Worker (The Engine Bridge)
# ============================================================
import requests
import json
import base64
import io
import torch
import time
from PIL import Image
from tamer_ocr.core.inference import greedy_decode
from tamer_ocr.data.dataset import preprocess_image

# 1. Ask user for the connection URL (Displayed in your local UI)
print("\\n" + "="*60)
print("🚀 HTTP WORKER CONNECTION SETUP")
print("="*60)
ngrok_url = input("Enter your Ngrok HTTP URL (e.g., https://abc.ngrok-free.dev): ").strip()

if ngrok_url.endswith('/'):
    ngrok_url = ngrok_url[:-1]

print(f"\\n✅ Target Backend: {ngrok_url}")
print("🎧 Waiting for incoming math images from your UI...")

while True:
    try:
        # 1. Poll for tasks
        res = requests.get(f"{ngrok_url}/worker/task")
        if res.status_code == 200:
            data = res.json()
            task_id = data.get('task_id', 'Unknown')
            print(f"\\n📥 Received Image Task! ID: {task_id}")
            
            if 'image_base64' in data:
                img_data = base64.b64decode(data['image_base64'])
                img = Image.open(io.BytesIO(img_data)).convert('RGB')
                
                temp_path = "/content/temp_task_image.png"
                img.save(temp_path)
                
                print("   ⚙️  Preprocessing image...")
                img_tensor, _, _ = preprocess_image(temp_path, config.img_height, config.img_width)
                img_tensor = img_tensor.to(device)
                
                print("   🧠 Running TAMER Model inference...")
                with torch.no_grad(), torch.autocast(device_type=device.type, dtype=torch.bfloat16):
                    pred_ids = greedy_decode(
                        model, img_tensor.unsqueeze(0),
                        tokenizer.sos_id, tokenizer.eos_id,
                        max_len=150, device=device
                    )
                
                latex_result = tokenizer.decode(pred_ids[0], skip_special=True)
                print(f"   ✅ Extracted LaTeX: {latex_result}")
                
                # 2. Push result
                post_res = requests.post(f"{ngrok_url}/worker/result", json={
                    "task_id": task_id,
                    "latex": latex_result
                })
                
                if post_res.status_code == 200:
                    print("📤 Successfully pushed LaTeX back to local backend!")
                else:
                    print(f"❌ Failed to push result: {post_res.text}")
            else:
                print("❌ Task missing 'image_base64'. Skipping.")
                
    except requests.exceptions.ConnectionError:
        pass
    except Exception as e:
        print(f"❌ Error processing task: {str(e)}")
        
    time.sleep(2.5)
"""
                lines = [line + "\\n" for line in new_code.split("\\n")]
                lines[-1] = lines[-1].strip("\\n")
                cell["source"] = lines

    with open(filename, "w") as f:
        json.dump(nb, f, indent=2)
    print(f"Updated {filename}")

update_nb("gpu_worker.ipynb")
update_nb("gpu_worker.txt")
update_nb("gpuworker.ipynb")
