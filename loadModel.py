########################################################################################################
# The RWKV Language Model - https://github.com/BlinkDL/RWKV-LM
########################################################################################################

from genericpath import exists
from typing import List
from src.model_run import RWKV_RNN
import numpy as np
import math
import os
import sys
import types
import time
import gc
import torch
from src.utils import TOKENIZER
from tqdm import tqdm
try:
    os.environ["CUDA_VISIBLE_DEVICES"] = sys.argv[1]
except:
    pass
import inquirer


def loadModel():
    files = os.listdir()
    # filter by ending in .pth
    files = [f for f in files if f.endswith(".pth")]

    questions = [
        inquirer.List('file',
                      message="What model do you want to use?",
                      choices=files,
                      ),
    ]
    file = inquirer.prompt(questions)["file"]

    torch.backends.cudnn.benchmark = True
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cuda.matmul.allow_tf32 = True
    np.set_printoptions(precision=4, suppress=True, linewidth=200)
    args = {}
    argsnums = {}

    ########################################################################################################
    # Step 1: set model & config
    # Do this first: pip install torchdynamo
    ########################################################################################################

    vocab_size = 50277

    # 'cpu' (already very fast) // 'cuda' // proc (faster then cpu, uses a fraction of the vram of cuda)
    args["RUN_DEVICE"] = inquirer.prompt([inquirer.List('RUN_DEVICE',
                                                        message="What device do you want to use?",
                                                        choices=[
                                                            "cpu", "cuda"],
                                                        )])["RUN_DEVICE"]

    # how many layers to offload to cuda, smaller number is slower, but uses less vram. // 0 -> n_layer // use to speed up proc as well
    numdevices = int(torch.cuda.device_count())
    layerdist = []
    if (args["RUN_DEVICE"] == "cuda"):
        for devic in range(numdevices):
            dev = inquirer.text(
                message=f"How many layers would you like on device {devic}?")
            if dev == "":
                dev = 100
            else:
                dev = int(dev)
            layerdist += [f"cuda:{devic}"] * dev
    print(layerdist)

    if (args["RUN_DEVICE"] == "cuda"):
        if (numdevices == 1):
            layerdist += ["proc"] * 100 + ["cuda:0"]
        else:
            layerdist += ["proc"] * 100 + [inquirer.prompt([inquirer.List('RUN_DEVICE',
                                                                          message="What device do you want to use for cuda streaming?",
                                                                          choices=list(map(lambda m: f"cuda:{m}", range(
                                                                                  numdevices))),
                                                                          )])["RUN_DEVICE"]]

    else:
        layerdist = ["cpu"]*100
    # fp32 // bf16 (saves VRAM, slightly less accurate) // fp16 (saves VRAM, slightly less accurate, can only be used with cuda, sometimes faster)
    args["FLOAT_MODE"] = inquirer.prompt([inquirer.List('FLOAT_MODE',
                                                        message="What float mode do you want to use?",
                                                        choices=[
                                                            "fp32", "bf16", "fp16"] if args["RUN_DEVICE"] == "cuda" else ["fp32", "bf16"],
                                                        )])["FLOAT_MODE"]

    # print config
    print("RUN_DEVICE:", args["RUN_DEVICE"])
    print("FLOAT_MODE:", args["FLOAT_MODE"])
    print("cudalayers:", argsnums["cudalayers"]
          if "cudalayers" in argsnums else "all")
    print("")

    torch.set_num_threads(12)
    # opt
    opt = "jit"  # none // jit

    if (args["RUN_DEVICE"] == "cpu" and args["FLOAT_MODE"] == "fp16"):
        raise (Warning("fp16 is only supported on cuda"))

    args["MODEL_NAME"] = file
    argsnums["ctx_len"] = 4068
    argsnums["vocab_size"] = vocab_size
    argsnums["head_qk"] = 0
    argsnums["pre_ffn"] = 0
    argsnums["grad_cp"] = 0
    argsnums["my_pos_emb"] = 0
    os.environ["RWKV_RUN_DEVICE"] = args["RUN_DEVICE"]

    ########################################################################################################
    # Step 2: set prompt & sampling stuffs
    ########################################################################################################
    model = RWKV_RNN(args, argsnums, layerdist)
    if (opt == "jit"):

        model = torch.jit.script(model)

    return model
