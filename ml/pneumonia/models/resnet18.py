import torch.nn as nn
from torchvision import models 

def build_resnet18_binary(pretrained: bool = True) -> nn.Module:
    m = models.resnet18(weights=models.ResNet18_Weights.DEFAULT if pretrained else None)
    in_features = m.fc.in_features
    m.fc = nn.Linear(in_features, 1)  # logits
    return m