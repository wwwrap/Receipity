import os
import json
from datasets import load_dataset

def fetch_samples():
    print("Downloading CORD samples from Hugging Face...")
    # Load 3 samples from the dataset train split
    dataset = load_dataset("naver-clova-ix/cord-v2", split="train[:3]")

    # Create directories if they don't exist
    os.makedirs("sampleData/images", exist_ok=True)
    os.makedirs("sampleData/annotations", exist_ok=True)
    
    for i, item in enumerate(dataset):
        # Save the image
        img_path = os.path.join("sampleData", "images", f"receipt_{i+1}.png")
        item['image'].save(img_path)

        # Handle ground truth data
        gt = item['ground_truth']
        if isinstance(gt, str):
            gt_data = json.loads(gt)
        else:
            gt_data = gt

        # Save the JSON annotation nicely formatted
        json_path = os.path.join("sampleData", "annotations", f"receipt_{i+1}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(gt_data, f, indent=4, ensure_ascii=False)

        print(f"Saved sample {i+1} successfully!")

    print("\nDone! Check your sampleData/ folder in VS Code.")

if __name__ == "__main__":
    fetch_samples()