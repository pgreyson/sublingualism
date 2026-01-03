#!/usr/bin/env python3
import os
import subprocess
import numpy as np
import json
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

def extract_frames(video_path, interval=1):
    """Extract frames at regular intervals"""
    output_dir = "temp_frames"
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract frames every N seconds
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vf', f'fps=1/{interval}',
        f'{output_dir}/frame_%04d.jpg',
        '-hide_banner',
        '-loglevel', 'error'
    ]
    
    print(f"Extracting frames every {interval}s...")
    subprocess.run(cmd)
    
    frame_files = sorted([f for f in os.listdir(output_dir) if f.endswith('.jpg')])
    print(f"Extracted {len(frame_files)} frames")
    
    return output_dir, frame_files

def setup_aws_embedding_pipeline():
    """Setup for AWS-based embedding generation"""
    
    pipeline_options = {
        "1. AWS Rekognition": {
            "description": "Use AWS Rekognition's DetectLabels for scene understanding",
            "setup": """
import boto3
rekognition = boto3.client('rekognition', region_name='us-east-1')

def get_rekognition_features(image_path):
    with open(image_path, 'rb') as img:
        response = rekognition.detect_labels(Image={'Bytes': img.read()})
    
    # Extract label confidence scores as features
    labels = {label['Name']: label['Confidence'] for label in response['Labels']}
    return labels
"""
        },
        
        "2. SageMaker + CLIP": {
            "description": "Deploy CLIP model on SageMaker for semantic embeddings",
            "setup": """
# Deploy CLIP on SageMaker endpoint
from transformers import CLIPProcessor, CLIPModel
import torch
from PIL import Image

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

def get_clip_embedding(image_path):
    image = Image.open(image_path)
    inputs = processor(images=image, return_tensors="pt")
    
    with torch.no_grad():
        image_features = model.get_image_features(**inputs)
    
    return image_features.numpy().flatten()
"""
        },
        
        "3. Lambda + Lightweight CNN": {
            "description": "Use Lambda with MobileNet for quick feature extraction",
            "setup": """
import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

# Load pre-trained MobileNetV2 (without top layer)
model = MobileNetV2(weights='imagenet', include_top=False, pooling='avg')

def get_mobilenet_features(image_path):
    img = image.load_img(image_path, target_size=(224, 224))
    x = image.img_to_array(img)
    x = np.expand_dims(x, axis=0)
    x = preprocess_input(x)
    
    features = model.predict(x)
    return features.flatten()
"""
        },
        
        "4. Local Embeddings (for testing)": {
            "description": "Generate simple color/texture features locally",
            "setup": """
from PIL import Image
import numpy as np
from scipy import stats

def get_local_features(image_path):
    img = Image.open(image_path)
    img_array = np.array(img.resize((64, 64)))  # Downsample
    
    # Extract features
    features = []
    
    # Color histogram for each channel
    for channel in range(3):
        hist, _ = np.histogram(img_array[:,:,channel], bins=16, range=(0,256))
        features.extend(hist / hist.sum())
    
    # Simple texture features (variance, entropy)
    gray = img.convert('L')
    gray_array = np.array(gray.resize((32, 32)))
    
    features.append(np.var(gray_array))
    features.append(stats.entropy(gray_array.flatten()))
    
    # Edge density
    edges = np.abs(np.diff(gray_array, axis=0)).sum() + np.abs(np.diff(gray_array, axis=1)).sum()
    features.append(edges / gray_array.size)
    
    return np.array(features)
"""
        }
    }
    
    return pipeline_options

def find_optimal_segments(embeddings, timestamps, min_segments=3, max_segments=10):
    """Find optimal number of segments using clustering"""
    
    n_frames = len(embeddings)
    if n_frames < min_segments:
        return []
    
    # Try different numbers of clusters
    scores = []
    for k in range(min_segments, min(max_segments + 1, n_frames)):
        kmeans = KMeans(n_clusters=k, random_state=42)
        labels = kmeans.fit_predict(embeddings)
        
        if k < n_frames:
            score = silhouette_score(embeddings, labels)
            scores.append((k, score, labels))
    
    # Find best clustering
    if scores:
        best_k, best_score, best_labels = max(scores, key=lambda x: x[1])
        print(f"Optimal segments: {best_k} (silhouette score: {best_score:.3f})")
        
        # Find transition points
        transitions = []
        for i in range(1, len(best_labels)):
            if best_labels[i] != best_labels[i-1]:
                transitions.append(timestamps[i])
        
        return transitions
    
    return []

def create_aws_terraform():
    """Generate Terraform config for AWS infrastructure"""
    
    terraform_config = """# AWS Infrastructure for Video Frame Embedding

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  default = "us-east-1"
}

# S3 bucket for video frames
resource "aws_s3_bucket" "frame_storage" {
  bucket = "sublingualism-frame-embeddings"
}

# Lambda function for frame processing
resource "aws_lambda_function" "frame_embedder" {
  filename      = "lambda_function.zip"
  function_name = "sublingualism-frame-embedder"
  role          = aws_iam_role.lambda_role.arn
  handler       = "index.handler"
  runtime       = "python3.9"
  memory_size   = 3008
  timeout       = 300
  
  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.frame_storage.bucket
    }
  }
}

# IAM role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "sublingualism-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Lambda permissions
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_s3_rekognition" {
  name = "lambda_s3_rekognition"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.frame_storage.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "rekognition:DetectLabels",
          "rekognition:DetectModerationLabels"
        ]
        Resource = "*"
      }
    ]
  })
}

# SageMaker endpoint (optional, for CLIP)
resource "aws_sagemaker_model" "clip_model" {
  name               = "sublingualism-clip"
  execution_role_arn = aws_iam_role.sagemaker_role.arn

  primary_container {
    image = "763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:1.12.0-gpu-py38"
    model_data_url = "s3://${aws_s3_bucket.frame_storage.bucket}/models/clip-model.tar.gz"
  }
}

# Output the Lambda function ARN
output "lambda_arn" {
  value = aws_lambda_function.frame_embedder.arn
}
"""
    
    with open('aws_infrastructure.tf', 'w') as f:
        f.write(terraform_config)
    
    print("Created: aws_infrastructure.tf")
    return terraform_config

# Main execution
if __name__ == "__main__":
    print("Frame Embedding Segmenter for Abstract Video")
    print("=" * 50)
    
    print("\nEmbedding Options:")
    options = setup_aws_embedding_pipeline()
    
    for key, option in options.items():
        print(f"\n{key}: {option['description']}")
    
    print("\n\nFor glitch/noise art, recommended approaches:")
    print("1. CLIP embeddings - captures semantic content despite visual noise")
    print("2. Statistical features - detects changes in noise patterns/textures")
    print("3. Frequency domain analysis - identifies rhythm changes in glitch patterns")
    
    print("\n\nNext steps:")
    print("1. Set up AWS infrastructure (run: terraform init && terraform apply)")
    print("2. Extract frames from video")
    print("3. Upload frames to S3")
    print("4. Run embedding generation on AWS")
    print("5. Cluster embeddings to find natural segment boundaries")
    
    # Generate Terraform config
    create_aws_terraform()
    
    print("\n\nLocal demo with color/texture features:")
    video_path = "/Volumes/Workspace/Downloads/charybdis_v2 (1080p).mp4"
    
    if os.path.exists(video_path):
        # Extract sample frames
        output_dir, frame_files = extract_frames(video_path, interval=10)  # Every 10 seconds
        print(f"\nExtracted frames to: {output_dir}/")