import json
from pathlib import Path

SAMPLE_DIR = Path(__file__).resolve().parent / "sampleData"

def fetch_samples():
    try:
        from datasets import load_dataset
    except ImportError:
        raise SystemExit("Install optional dataset tools: python -m pip install -r requirements-dev.txt") from None
    print("Downloading CORD samples from Hugging Face...")
    # Load 3 samples from the dataset train split
    dataset = load_dataset("naver-clova-ix/cord-v2", split="train[:3]")

    # Create directories if they don't exist
    (SAMPLE_DIR / "images").mkdir(parents=True, exist_ok=True)
    (SAMPLE_DIR / "annotations").mkdir(parents=True, exist_ok=True)
    
    for i, item in enumerate(dataset):
        # Save the image
        img_path = SAMPLE_DIR / "images" / f"receipt_{i+1}.png"
        item['image'].save(img_path)

        # Handle ground truth data
        gt = item['ground_truth']
        if isinstance(gt, str):
            gt_data = json.loads(gt)
        else:
            gt_data = gt

        # Save the JSON annotation nicely formatted
        json_path = SAMPLE_DIR / "annotations" / f"receipt_{i+1}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(gt_data, f, indent=4, ensure_ascii=False)

        print(f"Saved sample {i+1} successfully!")

    print("\nDone! Check your sampleData/ folder in VS Code.")

if __name__ == "__main__":
    fetch_samples()
