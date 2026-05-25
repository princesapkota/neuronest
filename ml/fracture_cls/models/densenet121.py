import torch.nn as nn
from torchvision import models

def build_densenet121_binary(pretrained: bool = True) -> nn.Module:
    model = models.densenet121(weights=models.DenseNet121_Weights.DEFAULT if pretrained else None)
    in_features = model.classifier.in_features
    model.classifier = nn.Linear(in_features, 1)
    return model