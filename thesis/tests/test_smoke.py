import torch

def test_cuda_available():
    print(f"CUDA is available: {torch.cuda.is_available()}")
    assert True
