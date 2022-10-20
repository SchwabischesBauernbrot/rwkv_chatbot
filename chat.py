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
import discord
import torch
from src.utils import TOKENIZER
from tqdm import tqdm
try:
    os.environ["CUDA_VISIBLE_DEVICES"] = sys.argv[1]
except:
    pass

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


TOKEN_MODE = "pile"
WORD_NAME = [
    "20B_tokenizer.json",
    "20B_tokenizer.json",
]  # [vocab, vocab] for Pile model
UNKNOWN_CHAR = None
vocab_size = 50277

# note; you can set MODEL_NAME to your fine-tuned model
size = "large"  # tini/mini/medium/medium-ext/large/xl/xxl

if (size == "tiny"):
    MODEL_NAME = "100"
    n_layer = 12
    n_embd = 768
    ctx_len = 1024

elif (size == "small"):
    MODEL_NAME = '/fsx/BlinkDL/rwkv-release/RWKV-4-Pile-430M-20220808-8066'
    n_layer = 24
    n_embd = 1024
    ctx_len = 1024
elif (size == "medium"):
    MODEL_NAME = '/fsx/BlinkDL/HF-MODEL/rwkv-4-pile-1b5/RWKV-4-Pile-1B5-20220903-8040'
    n_layer = 24
    n_embd = 2048
    ctx_len = 1024
elif (size == "medium-ext"):
    MODEL_NAME = '/fsx/BlinkDL/HF-MODEL/rwkv-4-pile-1b5/RWKV-4-Pile-1B5-20220929-ctx4096'
    n_layer = 24
    n_embd = 2048
    ctx_len = 4096
elif (size == "large"):
    MODEL_NAME = 'RWKV-4-Pile-3B-20221008-8023'
    n_layer = 32
    n_embd = 2560
    ctx_len = 1024
elif (size == "xl"):
    MODEL_NAME = '7100'
    n_layer = 32
    n_embd = 4096
    ctx_len = 1024


# 'cpu' (already very fast) // 'cuda' // proc (faster then cpu, uses a fraction of the vram of cuda)
args["RUN_DEVICE"] = "proc"
# how many layers to offload to cuda, smaller number is slower, but uses less vram. // 0 -> n_layer // use to speed up proc as well
argsnums["cudalayers"] = 32
# fp32 // bf16 (saves VRAM, slightly less accurate) // fp16 (saves VRAM, slightly less accurate, can only be used with cuda, sometimes faster)
args["FLOAT_MODE"] = "bf16"

# none // ray(slower but may have better answers)
os.environ["rwkv_sampler"] = "ray"
os.environ["rwkv_smpler_splits"] = "3"  # This is how many branches it checks
os.environ["rwkv_ray_depth"] = "2"  # This is how deep it goes in each branch

# set max threads to 12

torch.set_num_threads(12)

# opt
opt = "jit"  # none // jit

if (args["RUN_DEVICE"] == "cpu" and args["FLOAT_MODE"] == "fp16"):
    print(Warning("fp16 is only supported on cuda, workarounds may be slow"))


args["MODEL_NAME"] = MODEL_NAME
argsnums["n_layer"] = n_layer
argsnums["n_embd"] = n_embd
argsnums["ctx_len"] = ctx_len
argsnums["vocab_size"] = vocab_size
argsnums["head_qk"] = 0
argsnums["pre_ffn"] = 0
argsnums["grad_cp"] = 0
argsnums["my_pos_emb"] = 0
os.environ["RWKV_RUN_DEVICE"] = args["RUN_DEVICE"]

########################################################################################################
# Step 2: set prompt & sampling stuffs
########################################################################################################

# context = 'A'
# context = "\nIn the"
# context = '\nSugar:'

# context = "\n深圳是" # test Chinese
# context = "\n東京は" # test Japanese

###### A good prompt for chatbot ######
context = '''
The following is a conversation between a highly knowledgeable and intelligent AI assistant, called RWKV, and a human user, called User. In the following interactions, User and RWKV will converse in natural language, and RWKV will do its best to answer User’s questions. RWKV was built to be respectful, polite and inclusive. It knows a lot, and always tells the truth. The conversation begins.

User: OK RWKV, I’m going to start by quizzing you with a few warm-up questions. Who is currently the president of the USA?

RWKV: It’s Joe Biden; he was sworn in earlier this year.

User: What year was the French Revolution?

RWKV: It started in 1789, but it lasted 10 years until 1799.

User: Can you guess who I might want to marry?

RWKV: Only if you tell me more about yourself - what are your interests?

User: Aha, I’m going to refrain from that for now. Now for a science question. What can you tell me about the Large Hadron Collider (LHC)?

RWKV: It’s a large and very expensive piece of science equipment. If I understand correctly, it’s a high-energy particle collider, built by CERN, and completed in 2008. They used it to confirm the existence of the Higgs boson in 2012.

'''
# context = "hello world! I am your supreme overlord!"
NUM_TRIALS = 999
LENGTH_PER_TRIAL = 200

TEMPERATURE = 1.7
top_p = 0.8
top_p_newline = 0.9  # only used in TOKEN_MODE = char

DEBUG_DEBUG = False  # True False --> show softmax output

########################################################################################################

print(f'\nUsing {args["RUN_DEVICE"].upper()}. Loading {MODEL_NAME}...')

model = RWKV_RNN(args, argsnums)

if (opt == "jit"):

    model = torch.jit.script(model)
    model = torch.jit.optimize_for_inference(model)
    model = model.eval()


state = torch.zeros(
    argsnums["n_layer"] * 5, argsnums["n_embd"], device="cpu" if args["RUN_DEVICE"] == "cpu" else "cuda", dtype=torch.float32 if args["FLOAT_MODE"] == "fp32" else torch.bfloat16 if args["FLOAT_MODE"] == "bf16" else torch.float16)
for i in range(argsnums["n_layer"]):
    state[5*i+4] -= 1e30
init_state = state.clone()


print(f'\nOptimizing speed...')
model.forward([187], init_state)
gc.collect()
torch.cuda.empty_cache()

# input(0)

print(f'\nLoading tokenizer {WORD_NAME}...')
tokenizer = TOKENIZER(WORD_NAME, UNKNOWN_CHAR=UNKNOWN_CHAR)
if TOKEN_MODE == "pile":
    assert tokenizer.tokenizer.decode([187]) == '\n'

########################################################################################################

if tokenizer.charMode:
    context = tokenizer.refine_context(context)
    ctx = [tokenizer.stoi.get(s, tokenizer.UNKNOWN_CHAR) for s in context]
else:
    ctx = tokenizer.tokenizer.encode(context)
src_len = len(ctx)
src_ctx = ctx.copy()

print("\nYour prompt has " + str(src_len) + " tokens.")
print(
    "Note: currently the first run takes a while if your prompt is long, as we are using RNN to preprocess the prompt. Use GPT to build the hidden state for better speed.\n"
)

time_slot = {}
time_ref = time.time_ns()


def record_time(name):
    if name not in time_slot:
        time_slot[name] = 1e20
    tt = (time.time_ns() - time_ref) / 1e9
    if tt < time_slot[name]:
        time_slot[name] = tt


init_out = []

out = []
print(("-" * 50) + '\n' + context, end="")

print("torch.cuda.memory_allocated: %fGB" %
      (torch.cuda.memory_allocated(0)/1024/1024/1024))
print("torch.cuda.memory_reserved: %fGB" %
      (torch.cuda.memory_reserved(0)/1024/1024/1024))
print("torch.cuda.max_memory_reserved: %fGB" %
      (torch.cuda.max_memory_reserved(0)/1024/1024/1024))


for i in tqdm(range(src_len)):
    x = ctx[: i + 1]
    if i == src_len - 1:
        init_out, init_state = model.forward(x, init_state)
    else:
        oo, init_state = model.forward(
            x, init_state, preprocess_only=True)
gc.collect()
torch.cuda.empty_cache()


def ray_sampler(ctxx, chars, score, statein, depth=0, nla=0):

    out1, state1 = model.forward(ctxx+chars, statein[-1].clone())
    if TOKEN_MODE == "pile":
        out1[1] = -99  # disable <|endoftext|>
    out1[187] += nla
    ttt1 = tokenizer.sample_logits(
        out1,
        ctxx+chars,
        ctx_len,
        temperature=TEMPERATURE,
        top_p_usual=top_p,
        top_p_newline=top_p_newline,
    )
    ret = []
    if (depth < int(os.environ["rwkv_ray_depth"])):
        for nt in ttt1:
            ret += ray_sampler(ctxx+chars, chars +
                               [nt], score+out1[nt], statein + [state1], depth+1, nla)
    else:
        for nt in ttt1:
            ret.append(
                {"state": statein + [state1], "score": score+out1[nt], "chars": chars+[nt]})
    return ret


def sample(ctxx, state, nla):
    ctx = ctxx
    if os.environ["rwkv_sampler"] == "ray":

        rays = ray_sampler(ctxx, [], 0, [state], 0, nla)
        mx1 = max(rays, key=lambda x: x["score"])

        ctx += mx1["chars"]
        state = mx1["state"][-1]

        l = len(mx1["chars"])
        statein = mx1["state"]
    else:

        out, state = model.forward(ctxx, state)
        if TOKEN_MODE == "pile":
            out[0] = -99  # disable <|endoftext|>
        out[187] += nla
        ttt = tokenizer.sample_logits(
            out,
            ctx,
            ctx_len,
            temperature=TEMPERATURE,
            top_p_usual=top_p,
            top_p_newline=top_p_newline,
        )
        ctx += [ttt]
        statein = [state]

    return ctx, state, statein


print(("-" * 50) + '\n')

saveStates = {}


# bot.py

client = discord.Client(
    intents=discord.Intents.all())


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')


currstate = init_state
model_tokens = tokenizer.tokenizer.encode(context)

saveStates["empty"] = ([], state)
saveStates["questions"] = (model_tokens, init_state)


@client.event
async def on_message(message):
    global model_tokens, currstate
    # print(
    #     f"message received({message.guild.name}:{message.channel.name}):", message.content)

    if message.author.bot:
        return

    msg = message.content.strip()

    if msg == '+reset_drkv' or msg == '+drkv_reset':
        model_tokens = tokenizer.tokenizer.encode(context)
        currstate = init_state

        await message.reply(f"Chat reset. This is powered by RWKV-4-{size} Language Model.")
        return

    if msg[:11] == '+drkv_save ':
        saveStates[msg[11:]] = (model_tokens, currstate)
        await message.reply(f"Saved state {msg[11:]}")
        return

    if msg[:11] == '+drkv_load ':
        if msg[11:] in saveStates:
            model_tokens, currstate = saveStates[msg[11:]]
            await message.reply(f"Loaded state {msg[11:]}")
        else:
            await message.reply(f"State {msg[11:]} not found")
        return

    if msg[:11] == '+drkv_list ':
        await message.reply(f"Saved states: {', '.join(saveStates.keys())}")
        return
    if msg[:6] == '+drkv ':

        real_msg = msg[6:].strip()
        new = f"User: {real_msg}\n\nRWKV:"
        tknew = tokenizer.tokenizer.encode(new)
        print(f'### add ###\n[{new}]')
        before = len(model_tokens)
        model_tokens = model_tokens + tknew
        begin = len(model_tokens)
        for o in tqdm(range(len(tknew))):
            r, currstate = model.forward(
                model_tokens[:before + o], currstate, preprocess_only=True)
        for i in tqdm(range(100)):
            if i <= 0:
                newline_adj = -999999999
            elif i <= 30:
                newline_adj = -2
            elif i <= 70:
                newline_adj = 0
            elif i <= 97:
                newline_adj = i - 70
            else:
                newline_adj = 999999999

            tt, currstate, statelist = sample(
                model_tokens, currstate, 0)

            model_tokens = tt
            currstate = statelist[-1]
            if "\n\n" in tokenizer.tokenizer.decode(tt[begin:]):
                print(tokenizer.tokenizer.decode(tt[begin:]))
                if tokenizer.tokenizer.decode(tt[begin:])[-1] != "\n":
                    model_tokens = model_tokens[:-1]
                    currstate = statelist[-2]
                break
        send_msg = tokenizer.tokenizer.decode(model_tokens[begin:]).strip()
        print(f'### send ###\n[{send_msg}]')
        await message.reply(send_msg)

client.run(os.environ["TOKEN"])
