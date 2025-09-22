# Model Training on RTX 3060 12GB

Status: Draft
Last Updated: 2025-09-21

## GPU Capability Summary
RTX 3060 12GB provides excellent training capabilities for small-to-medium language models with proper optimization. The 12GB VRAM is the key constraint, but modern techniques make efficient use of it.

## What You Can Train (Feasibility Matrix)

| Model | Parameters | Base Memory | Full Fine-tune | LoRA | QLoRA | 4-bit |
|-------|------------|-------------|----------------|------|-------|-------|
| GPT-2 Base | 124M | ~500MB | ✅ Easy | ✅ | ✅ | ✅ |
| GPT-2 Medium | 355M | ~1.4GB | ✅ Good | ✅ | ✅ | ✅ |
| GPT-2 Large | 774M | ~3GB | ⚠️ Tight | ✅ | ✅ | ✅ |
| GPT-2 XL | 1.5B | ~6GB | ❌ | ✅ Good | ✅ | ✅ |
| Llama 2 7B | 7B | ~14GB | ❌ | ❌ | ✅ Good | ✅ |
| Mistral 7B | 7B | ~14GB | ❌ | ❌ | ✅ Good | ✅ |
| CodeLlama 7B | 7B | ~14GB | ❌ | ❌ | ✅ Good | ✅ |

Legend: ✅ Comfortable, ⚠️ Requires optimization, ❌ Not feasible

## Recommended Training Strategies

### 1. Full Fine-tuning (GPT-2 Base/Medium)
Best for: Domain adaptation on your ebook corpus
```yaml
# config/training.yml
full_finetune:
  model: "gpt2-medium"  # 355M params
  batch_size: 2
  gradient_accumulation: 4  # effective batch = 8
  max_length: 512
  learning_rate: 5e-5
  fp16: true  # saves ~50% memory
  gradient_checkpointing: true
```

Memory usage: ~6-8GB (comfortable)

### 2. LoRA Fine-tuning (Up to GPT-2 XL)
Best for: Parameter-efficient adaptation
```yaml
lora_finetune:
  model: "gpt2-xl"  # 1.5B params
  lora_r: 16
  lora_alpha: 32
  lora_dropout: 0.1
  batch_size: 1
  gradient_accumulation: 8
  fp16: true
```

Memory usage: ~8-10GB (good fit)
Training time: ~2-3x faster than full fine-tune

### 3. QLoRA (7B Models!)
Best for: Training larger models efficiently
```yaml
qlora_finetune:
  model: "mistralai/Mistral-7B-v0.1"
  load_in_4bit: true
  bnb_4bit_compute_dtype: "bfloat16"
  lora_r: 64
  lora_alpha: 16
  batch_size: 1
  gradient_accumulation: 16
```

Memory usage: ~9-11GB (fits!)
Quality: Very close to full fine-tune

## Optimization Techniques for 12GB

### Memory Optimizations
1. **Gradient Checkpointing**: Trade compute for memory (~30% slower, 50% less memory)
2. **Mixed Precision (FP16/BF16)**: ~50% memory reduction
3. **4-bit Quantization**: ~75% memory reduction (QLoRA)
4. **Gradient Accumulation**: Simulate larger batches with smaller memory
5. **CPU Offloading**: Move optimizer states to RAM when needed

### Training Configuration (Recommended)
```python
# Aggressive memory optimization
training_args = TrainingArguments(
    output_dir="./models/",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    num_train_epochs=3,
    fp16=True,  # or bf16 if supported
    gradient_checkpointing=True,
    dataloader_pin_memory=False,
    remove_unused_columns=True,
    save_strategy="steps",
    save_steps=500,
    logging_steps=50,
)
```

## Practical Training Times (Estimates)

### GPT-2 Medium on 50k sequences
- Full fine-tune: ~6-8 hours
- LoRA: ~3-4 hours
- Dataset: ~25MB of your processed ebooks

### Mistral 7B QLoRA on 50k sequences
- QLoRA: ~12-16 hours
- Much better quality than GPT-2
- Can handle longer contexts (4k vs 1k tokens)

## Memory Monitoring Commands
```bash
# During training, monitor GPU usage
nvidia-smi -l 1

# Or install nvtop for better monitoring
pip install nvitop
nvitop
```

## Integration with Your Pipeline

### 1. Export Training Data (Add to pipeline.py)
```python
def export_for_training(processed_result, target_length=512):
    """Convert raw_chunks to training sequences."""
    sequences = []
    for chunk in processed_result["raw_chunks"]:
        tokens = len(chunk.split())
        if 50 <= tokens <= target_length:
            sequences.append({
                "text": chunk,
                "length": tokens,
                "book": processed_result["metadata"]["title"]
            })
    return sequences
```

### 2. Batch Processing Script
```python
# scripts/prepare_training_data.py
def collect_all_books():
    """Process all books and export training sequences."""
    all_sequences = []
    for book_file in Path("books/").glob("*.epub"):
        processed = process_ebook(book_file)
        sequences = export_for_training(processed)
        all_sequences.extend(sequences)
    
    # Save as training dataset
    with open("training_data.jsonl", "w") as f:
        for seq in all_sequences:
            f.write(json.dumps(seq) + "\n")
```

## Model Selection Recommendations

### For Your Use Case (Ebook RAG):

**Best Overall: Mistral 7B + QLoRA**
- Excellent instruction following
- Good reasoning about literature
- 4k context window (handles long chunks)
- Fits comfortably with QLoRA

**Budget/Speed Option: GPT-2 Medium + Full Fine-tune**  
- Fast training
- Good for domain adaptation
- Plenty of memory headroom
- Can run multiple experiments

**Experimental: CodeLlama 7B + QLoRA**
- Excellent at structured reasoning
- Good for analysis tasks
- Handles complex queries well

## Expected Results Timeline

### Week 1: GPT-2 Medium
- Process 10-20 books → ~30k training sequences
- Full fine-tune in 6-8 hours
- Immediate improvement on domain-specific queries

### Week 2-3: Mistral 7B QLoRA
- Same dataset, much longer training (12-16 hours)
- Significant quality jump
- Better handling of complex literary analysis

## Hardware Monitoring & Safety

### Temperature Monitoring
```bash
# Keep GPU under 80°C during long training runs
watch -n 1 "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits"
```

### Power Limit (Optional)
```bash
# Reduce power limit to 200W if overheating (default ~220W)
sudo nvidia-smi -pl 200
```

## Troubleshooting Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| CUDA out of memory | Batch too large | Reduce batch_size, increase gradient_accumulation |
| Training very slow | No mixed precision | Add fp16=True or bf16=True |
| Model quality poor | Learning rate wrong | Try 5e-5 for full, 2e-4 for LoRA |
| GPU underutilized | Sequence too short | Increase max_length to 512-1024 |

## Cost-Benefit Analysis

### Electricity Cost (Rough)
- RTX 3060: ~220W under load
- Training 8 hours: ~1.8 kWh
- At $0.12/kWh: ~$0.22 per training run
- Very economical compared to cloud GPU

### Quality vs Training Time
1. GPT-2 Medium (6h): Good domain adaptation
2. GPT-2 Large LoRA (4h): Better reasoning, same cost
3. Mistral 7B QLoRA (15h): Production quality, 3x time investment

## Next Steps Implementation Plan

1. **Phase 1**: Add training data export to existing pipeline
2. **Phase 2**: Implement GPT-2 Medium training script
3. **Phase 3**: Experiment with LoRA on larger models
4. **Phase 4**: QLoRA training on Mistral 7B
5. **Phase 5**: Integrate best model back into RAG system

## Dependencies to Add
```bash
poetry add transformers torch datasets accelerate bitsandbytes peft wandb
```

---
End of document.