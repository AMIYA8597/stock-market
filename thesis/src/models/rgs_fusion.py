import torch
import torch.nn as nn
import torch.nn.functional as F

class RGSFusion(nn.Module):
    def __init__(self, seq_dim, img_dim, num_regimes=2, num_classes=1, dropout=0.2):
        super(RGSFusion, self).__init__()
        
        # Sequence Encoder (Simulating PatchTST / TSMixer)
        self.seq_encoder = nn.Sequential(
            nn.Linear(seq_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 32)
        )
        
        # Image Encoder (Simulating JKX-CNN / ViT-Tiny)
        self.img_encoder = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Flatten(),
            nn.Linear(16 * (img_dim // 2) * (img_dim // 2), 32), # Assuming square input
            nn.Dropout(dropout)
        )
        
        # Modality Gate
        # π_t is the regime posterior of shape (batch, num_regimes)
        gate_input_dim = num_regimes + 32 + 32
        self.gate = nn.Sequential(
            nn.Linear(gate_input_dim, 2), # 2 modalities
            nn.Softmax(dim=1)
        )
        
        # Regime Experts
        self.experts = nn.ModuleList([
            nn.Linear(32, num_classes) for _ in range(num_regimes)
        ])
        
    def forward(self, x_seq, x_img, pi_t):
        z_S = self.seq_encoder(x_seq)
        z_I = self.img_encoder(x_img)
        
        # Gate weights
        gate_in = torch.cat([pi_t, z_I, z_S], dim=1)
        alpha = self.gate(gate_in) # shape: (batch, 2)
        
        # Fused representation
        h_fused = alpha[:, 0:1] * z_I + alpha[:, 1:2] * z_S
        
        # Mixture of experts based on HMM regime posteriors pi_t
        out = 0
        for k in range(len(self.experts)):
            expert_out = torch.sigmoid(self.experts[k](h_fused))
            out += pi_t[:, k:k+1] * expert_out
            
        return out, alpha, z_I, z_S

def compute_loss(out, y, z_I, z_S, alpha, aux_weight=0.1, entropy_weight=0.01):
    bce = F.binary_cross_entropy(out, y)
    
    # Simulate auxiliary heads for individual modalities
    # (assuming we have linear layers for them, omitted for brevity, so mock loss here)
    aux_loss = 0 # F.binary_cross_entropy(...)
    
    # Gate entropy to encourage diversity
    h_ent = -torch.mean(torch.sum(alpha * torch.log(alpha + 1e-8), dim=1))
    
    return bce + aux_weight * aux_loss + entropy_weight * h_ent

