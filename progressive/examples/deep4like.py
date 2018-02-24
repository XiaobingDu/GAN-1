import braindecode
from torch import nn
from GAN.progressive.layers import Reshape
from GAN.progressive.modules import ProgressiveGenerator,ProgressiveGeneratorBlock,
                                    ProgressiveDiscriminator,ProgressiveDiscriminatorBlock
from GAN.GAN.modules import LayerNorm,PixelShuffle1d,PixelShuffle2d
from GAN.GAN.train_modules import WGAN_I_Generator,WGAN_I_Discriminator

input_size = 972

def create_disc_blocks(n_chans):
    def create_conv_sequence(in_filters,out_filters):
        return nn.Sequential(nn.Conv1d(in_filters,out_filters,9,padding=4),
                                nn.LayerNorm(out_filters),
                                nn.LeakyReLU(0.2),
                                nn.Conv1d(out_filters,out_filters,3,stride=3),
                                nn.LayerNorm(out_filters),
                                nn.LeakyReLU(0.2))
    def create_in_sequence(n_chans,out_filters):
        return nn.Sequential(nn.Conv2d(1,out_filters,(9,1),padding=4),
                                nn.Conv2d(out_filters,out_filters,(1,n_chans)),
                                nn.LayerNorm(out_filters),
                                nn.LeakyReLU(0.2),
                                Reshape([[0],[1],[2]]))
    blocks = []
    tmp_block = ProgressiveGeneratorBlock(
                              create_conv_sequence(25,25),
                              create_in_sequence(n_chans,25)
                              )
    blocks.append(tmp_block)
    tmp_block = ProgressiveGeneratorBlock(
                              create_conv_sequence(25,50),
                              create_in_sequence(n_chans,25)
                              )
    blocks.append(tmp_block)
    tmp_block = ProgressiveGeneratorBlock(
                              create_conv_sequence(50,100),
                              create_in_sequence(n_chans,50)
                              )
    blocks.append(tmp_block)
    tmp_block = ProgressiveGeneratorBlock(
                              nn.Sequential(create_conv_sequence(100,200),
                                            Reshape([[0],-1]),
                                            nn.Linear(200*12,1)),
                              create_in_sequence(n_chans,100))
    blocks.append(tmp_block)
    return blocks


def create_gen_blocks(n_chans,z_vars):
    def create_conv_sequence(in_filters,out_filters):
        return nn.Sequential(nn.Conv1d(in_filters,3*out_filters,9,padding=4),
                                PixelShuffle1d([3])
                                nn.BatchNorm2d(out_filters),
                                nn.ReLu())
    def create_out_sequence(n_chans,in_filters):
        return nn.Sequential(nn.Conv1d(in_filters,n_chans*in_filters,1),
                                nn.Conv1d(n_chans*in_filters,n_chans,9,padding=4),
                                Reshape([[0],[1],[2],-1]),
                                nn.PixelShuffle2d([1,n_chans]),
                                nn.Tanh())
    blocks = []
    tmp_block = ProgressiveGeneratorBlock(
                                nn.Sequential(nn.Linear(z_vars,200*12),
                                                nn.BatchNorm1d(200*12),
                                                nn.ReLu(),
                                                Reshape([[0],200,-1])
                                                create_conv_sequence(200,100)),
                                create_out_sequence(n_chans,100)
                                )
    blocks.append(tmp_block)
    tmp_block = ProgressiveGeneratorBlock(
                                create_conv_sequence(100,50),
                                create_out_sequence(n_chans,50)
                                )
    blocks.append(tmp_block)
    tmp_block = ProgressiveGeneratorBlock(
                                create_conv_sequence(50,25),
                                create_out_sequence(n_chans,25)
                                )
    blocks.append(tmp_block)
    tmp_block = ProgressiveGeneratorBlock(
                                create_conv_sequence(25,25),
                                create_out_sequence(n_chans,25)
                                )
    blocks.append(tmp_block)
    return blocks


class Generator(WGAN_I_Generator):
    def __init__(n_chans,z_vars):
        super(Generator,self)()
        self.model = ProgressiveGenerator(create_gen_blocks(n_chans,z_vars))

    def forward(self,input,alpha=1.,upsample_scale=3):
        return self.model(input,alpha,upsample_scale)

class Discriminator(WGAN_I_Discriminator):
    def __init__(n_chans):
        super(Discriminator,self)()
        self.model = ProgressiveDiscriminator(n_chans)

    def forward(self,input,use_std=True):
        return self.model(input,use_std)
