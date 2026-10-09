import os
import json
from backend.inference_engine import extract_and_parse

def evaluate_samples():
    image_dir = "sampleData/images"
    json_dir = "sampleData/annotations"

    if not os.path.exists(image_dir):
        print(f"Directory {image_dir} not found. Drop your sample images there!")
        return

    print("--- Running Dataset Evaluation ---")
    
    for filename in os.listdir(image_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            img_path = os.path.join(image_dir, filename)
            print(f"\nProcessing image: {filename}")

            # Run your backend inference engine
            merchant, date, total, raw_text = extract_and_parse(img_path)
            
            print(f" -> Extracted Merchant: {merchant}")
            print(f" -> Extracted Date: {date}")
            print(f" -> Extracted Total: {total}")

            # Optional: Compare against CORD ground truth JSON if available
            json_name = os.path.splitext(filename)[0] + ".json"
            json_path = os.path.join(json_dir, json_name)
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    ground_truth = json.load(f)
                    print(f" -> Ground Truth loaded successfully for validation.")

if __name__ == "__main__":
    evaluate_samples()