# Qwen 2.5 7B Fine-Tuning Guide (VietLabor AI)

## Objective
Supervised Fine-Tuning (SFT) using LoRA / QLoRA on domain Vietnamese labor law datasets:
- Can Tho labor situations
- Thai Nguyen dispute cases
- 1,000 synthetic multi-turn statutory dialogues

## Recommended Hyperparameters
- Base Model: `Qwen/Qwen2.5-7B-Instruct`
- Precision: `4-bit (bitsandbytes NF4)` or `bfloat16`
- LoRA Rank ($r$): `16`
- LoRA Alpha ($\alpha$): `32`
- LoRA Target Modules: `q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj`
- Learning Rate: `2e-4` (Cosine schedule, warmup 5%)
- Batch Size: `4` per device with Gradient Accumulation `4` (effective batch `16`)
- Max Sequence Length: `2048` tokens
- Epochs: `3`
