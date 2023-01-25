import socketserver
import json
import http.server
import webbrowser
from rwkvChatPersonalities import Personaities
import numpy as np
import os
from typing import Dict as dict
import gc

try:
    import inquirer
except:
    install = not input(
        "inquirer not installed. Would you like to install it? (Y/n)") in ["n", "N"]
    if install:
        os.system("pip3 install inquirer")
        import inquirer
    else:
        print("Exiting...")
        exit()
try:
    from scipy.special import softmax
except:
    install = inquirer.prompt([inquirer.Confirm(
        'install',
        message="scipy not installed. Would you like to install it?",
        default=True,
    )])["install"]
    if install:
        os.system("pip3 install scipy")
        from scipy.special import softmax
    else:
        print("Exiting...")
        exit()

try:
    import torch
except:
    install = inquirer.prompt([inquirer.Confirm(
        'install',
        message="torch not installed. Would you like to install it? NOTE: AMD GPU users should double check https://pytorch.org/get-started/locally/",
        default=True,
    )])["install"]
    if install:
        # test if amd gpu

        os.system(
            "pip3 install torch torchvision torchaudio")
        import torch
    else:
        print("Exiting...")
        exit()

# check if yarn installed
if os.system("yarn --version"):
    install = inquirer.prompt([inquirer.Confirm(
        'install',
        message="yarn not installed. Would you like to install it?",
        default=True,
    )])["install"]
    if install:
        if os.system("npm install -g yarn"):
            print("Failed to install yarn using npm. you need to install nodejs manually from https://nodejs.org/en/download/")
            exit()
    else:
        print("Exiting...")
        exit()

from rwkvstic.rwkvMaster import RWKVMaster


async def runWebsite(model: RWKVMaster):
    os.chdir("web-interface")
    os.system("yarn")
    os.system("yarn build")
    os.chdir("..")

    files = os.listdir()
    # filter by ending in .pth
    files = [f for f in files if f.endswith(".pth")]

    ###### A good prompt for chatbot ######

    # context = "hello world! I am your supreme overlord!"

    ########################################################################################################

    print(f'\nOptimizing speed...')

    gc.collect()
    torch.cuda.empty_cache()

    ########################################################################################################

    print(
        "Note: currently the first run takes a while if your prompt is long, as we are using RNN to preprocess the prompt. Use GPT to build the hidden state for better speed.\n"
    )

    print("torch.cuda.memory_allocated: %fGB" %
          (torch.cuda.memory_allocated(0)/1024/1024/1024))
    print("torch.cuda.memory_reserved: %fGB" %
          (torch.cuda.memory_reserved(0)/1024/1024/1024))
    print("torch.cuda.max_memory_reserved: %fGB" %
          (torch.cuda.max_memory_reserved(0)/1024/1024/1024))

    people: dict[str, str] = {}

    progress = {}

    for P, personality in Personaities.items():
        people[P] = model.loadContext(
            ctx="\n", newctx=personality, statex=model.emptyState)[1]

    class S(http.server.SimpleHTTPRequestHandler):

        def do_OPTIONS(self):
            self.send_response(200, "ok")
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods',
                             'GET, POST, OPTIONS')
            self.send_header("Access-Control-Allow-Headers",
                             "X-Requested-With, Content-Type")
            self.end_headers()

        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')

            if "css" in self.path:
                self.send_header('Content-type', 'text/css')
            elif "js" in self.path:
                self.send_header('Content-type', 'text/javascript')
            else:
                self.send_header('Content-type', 'text/html')

            self.end_headers()
            if "ping" in self.path:
                self.wfile.write("pong".encode('utf-8'))
                return
            if (self.path == "/"):
                self.path = "/index.html"
            if (self.path == "/personalities.json"):
                self.wfile.write(json.dumps(
                    list(people.keys())).encode('utf-8'))
                return
            if ("/progress" in self.path):
                self.wfile.write(
                    json.dumps(progress.get(self.path.split("/")[-1])).encode('utf-8'))
                return
            # self._set_response()
            self.wfile.write(
                open("web-interface/build/"+self.path, "rb").read())

        def do_POST(self):
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'text/html')
            if (self.path == "/progress"):
                state = json.loads(self.rfile.read(
                    int(self.headers['Content-Length'])).decode('utf-8'))

                progress[state["key"]] = state["state"]
                self.wfile.write("ok".encode('utf-8'))
                return

            self.end_headers()

            # Get body
            content_length = int(self.headers['Content-Length'])

            body = self.rfile.read(content_length)
            body = body.decode('utf-8')

            # get json
            body = json.loads(body)
            print(body["message"])

            character = body.get("character", list(people.keys())[0])

            body["state"] = progress.get(
                body.get("state", body["key"]), None)

            if body["state"] is None:
                body["state"] = people[character]
            else:
                body["state"] = (
                    list(map(lambda xx: model.initTensor(torch.tensor(xx)), body["state"])))

            progresskey = body["key"]

            tokens = (
                body["message"]+f"\n\nLong Expert Full Response:")

            def updateProgress(x):

                # send current chunk
                # the eyes emoji
                emoj = "👀"
                self.wfile.write(
                    json.dumps({"response": emoj, "done": False, "progress": len(model.tokenizer.decode(x))}).encode('utf-8'))

            model.loadContext(
                ctx="\nUser", newctx=tokens, statex=body["state"], progressCallBack=updateProgress)
            currentData = (tokens, model.getState())

            ln = len(currentData[0])

            response = ""

            for i in range(400):
                x = model.forward(state=currentData[1])["output"]
                response += x
                self.wfile.write(
                    json.dumps({"done": False, "response": response.replace("\nUser", ""), "progress": -1}).encode('utf-8'))

                currentData = (currentData[0]+x, model.getState())
                if (currentData[0]).strip().endswith(("\nUser")):
                    break

            tokens = currentData[0][ln:]

            # flatten
            print(tokens)

            out = {}

            out["response"] = tokens + ":"
            out["done"] = True
            out["progress"] = -1
            out["state"] = progresskey

            # recursively convert state to number from tensor
            state = currentData[1]
            ns = []
            for i in range(len(state)):
                try:
                    ns += [np.array(state[i].float().cpu()).tolist()]
                except:
                    ns += [np.array(state[i]).tolist()]

            progress[progresskey] = ns

            # set content length
            out = json.dumps(out).encode("utf8")

            self.wfile.write(out)
            # end connection
            self.close_connection = True

    httpd = socketserver.ThreadingTCPServer(('', int(input("Port:"))), S)
    # open browser
    if (input("Open browser? (y/N)") == "y"):
        webbrowser.open("http://localhost:"+str(httpd.server_address[1]))

    httpd.serve_forever()
