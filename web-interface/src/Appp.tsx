import "./App.scss";
import React, { useState } from "react";
import Message, {
  MessageProps,
  MessageSide,
  MessageType,
} from "./components/message/Message";
import TextField from "@mui/material/TextField";
import { Button } from "@mui/material";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";
import crow from "./images/crow.png";
import { Nav } from "./components/toolbar/toolbar";
// import png

type RwkvState = [number[], number[], number[], number[]] | undefined;

const mess: MessageProps[] = [
  {
    text: "Say Hello To RWKV!",
    type: MessageType.Info,
    side: MessageSide.Left,
  },
];

function App() {
  const [messages, setMessages] = useState(mess);
  const [state, setState] = useState<RwkvState>(undefined);
  const [currentMessage, setCurrentMessage] = useState("");
  // const [personalities, setPersonalities] = useState<string[]>([]);
  // const [character, setCharacter] = useState("RWKV");
  const [darkmode, setDarkmode] = useState(true);
  // set state to current address
  const [server, setServer] = useState(document.location.href);

  const darkTheme = createTheme({
    palette: {
      mode: darkmode ? "dark" : "light",
    },
  });

  const getMessage = async (message: string, state: RwkvState) => {
    // Randomly generated guid:
    const id = Math.random().toString(36).substring(2, 15);
    // do a fetch to the server
    const myresponse = fetch(server, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: message,
        state: state,
        // character: character,
        key: id,
      }),
    });

    const streamReader = (await myresponse).body?.getReader();

    if (streamReader) {
      var intext = "";
      var buff = "";
      console.log(intext);
      while (true) {
        const { done, value } = await streamReader.read();
        if (done) {
          break;
        }
        if (value) {
          try {
            intext = buff + new TextDecoder("utf-8").decode(value);
            console.log(intext);
            var {
              progress,
              response,
              state: mystate,
              done: ddone,
            } = JSON.parse("{" + intext.split("{").pop());
          } catch (e) {
            console.log(e);
            continue;
          }
          buff = "";

          if (mystate) {
            setState(mystate);
          }

          setMessages([
            ...messages,
            {
              text:
                progress > 0
                  ? message.slice(0, progress) + "|" + message.slice(progress)
                  : message,
              timeSent: new Date(),
              icon: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAOEAAADhCAMAAAAJbSJIAAAAeFBMVEX///8AAACAgIB8fHz19fXp6emNjY37+/umpqbY2NiYmJiwsLB2dnb4+PgwMDCtra2UlJTKysq/v7/R0dGdnZ1eXl4qKipvb2/v7+9ISEhRUVHg4OATExMLCwsiIiJnZ2eIiIhBQUE6OjrDw8NFRUVZWVkbGxu4uLjqLqXEAAAEJElEQVR4nO3di3aiMBAGYOMNEPCCN6pWq1Z9/zfcspazPZZISAZmcP/vCfIfYhKSMHY6AAAAAAAAAAAAAAAAAAAAAK+nPwhCf5jxJ8Ggz90cYvF8sVypn1aX0fx1Us6jnSryvp5xN42CNylMl/Nj7gY68vz904BK7Ratzjgfl+TL7M/czbTmrQ3yZQ4tHXOCq2HAL3Puxtp4PsI8WnA3t7qPSgGVirgbXJXpT/CfJXeTqzlUDtiyiJFFwK8hlbvZ5oZWAZXqcjfclG8ZUKkRd9PNBNYBWzIveiYrNZ19G1Y3dqNMrgWjzdwpoFLyl+EufTSz4w5Qxn4czQ25IzznvTsnVLIHG/dHKHxSdJopcjvJD3FGEFCpkDvGE9XfmYpcuGPoxSQBlUq5g2glRAkn3EG0qu5c6Mhduq3KG2+GO4hOnyqg2nJH0aCZKzIJdxSNG1lCnzuKxpQsodTNU5stxGIb7igaF7KER+4oGm9kCU/cUTSOSGhszB1F4/V76YYsodSRZkmW8I07ikaPLKHUg7aQLOGUO4rGmSzhjTuKxpYsodjbYGQJuYNoUS29pU4WNDveGakDTaczIEoo+CSYZt0mdVWaoemmcjspVTeVutP2F8XCTe5+cIbiIQbcIZ5zf4hSV905933vAXeEMq7Dqegz7rtPp4CS58Kc2xuG8GHmzuVFWOqBxQP7m21r7qabst2Sknpc8ZtntwI/Sb5I8yA+WQRctShgx2Z3+Ohxt7miqpeHLm0LWPXCfmuu6f9U5eKC1KsJJVLTWeMifrWtlRh9oCd1h9uINyrNN2zXJFHg6ZfA10X7htACs15xZ91FYs8nKusHi8dRZzkKWt89H3nBLfQz4S14ib4JAAAAAAAAAC8n7qfpdjYJ/dGdH05m2zTtt7ra3rdtkIyi5al4r+06XkbTW7Bt66ZNkHxszAoQrDbdRPCFyyLxeVr9iHQ8TNqxvZgmXZsD4O+U3ZvwQ5pg4f4N4mYqtsfOorJapaaua3mVhuIz3SdBd+uzpLlkHhEU3ikIOZMxj2wtxk1T4yH/jegb3WeVxT5Dzgc5sC2QWM0H14MMaOrtmDhwTCAB3df3JjZNZ2w4X+MZU+rJz0zU2IrOLy6T34BmKkYP6p4fnjk2MKzSfc5sp/YqWTy/wJ/qvQse05VNsPdW44tySlbMy8m1tjE1pXr/c7WrKSJJYUsaNV16b34Zo1fLlxnlN0WbVEMtXrqSEDToV6n1vcjbWVEHpCrcSYe6Uq2ccTS3pw3oWmm9DrR7qvzL0d9IF6ixvE5KPO1TFS2hRfmuSFcBihLlaCprPZOjXNdQFXmmRflFX5c7TCEkREIk5IeESIiE/JAQCZGQHxIiIRLyQ8IqJG6XKtUjTBj2uvL0JP/HHgAAAAAAAAAAAAAAAAAAAPyf/gCZuUm9oVCsnAAAAABJRU5ErkJggg==",
            },
            {
              text: response,
              timeSent: new Date(),
              side: MessageSide.Right,
              icon: crow,
            },
          ]);
          if (ddone) {
            break;
          }
        }
      }
    }

    // response.then((data) =>
    //   data.json().then((datajson: { message: string; state: RwkvState }) => {
    //     setState(datajson.state);
    //     setMessages([
    //       ...messages,
    //       {
    //         text: message,
    //         timeSent: new Date(),
    //         icon: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAOEAAADhCAMAAAAJbSJIAAAAeFBMVEX///8AAACAgIB8fHz19fXp6emNjY37+/umpqbY2NiYmJiwsLB2dnb4+PgwMDCtra2UlJTKysq/v7/R0dGdnZ1eXl4qKipvb2/v7+9ISEhRUVHg4OATExMLCwsiIiJnZ2eIiIhBQUE6OjrDw8NFRUVZWVkbGxu4uLjqLqXEAAAEJElEQVR4nO3di3aiMBAGYOMNEPCCN6pWq1Z9/zfcspazPZZISAZmcP/vCfIfYhKSMHY6AAAAAAAAAAAAAAAAAAAAAK+nPwhCf5jxJ8Ggz90cYvF8sVypn1aX0fx1Us6jnSryvp5xN42CNylMl/Nj7gY68vz904BK7Ratzjgfl+TL7M/czbTmrQ3yZQ4tHXOCq2HAL3Puxtp4PsI8WnA3t7qPSgGVirgbXJXpT/CfJXeTqzlUDtiyiJFFwK8hlbvZ5oZWAZXqcjfclG8ZUKkRd9PNBNYBWzIveiYrNZ19G1Y3dqNMrgWjzdwpoFLyl+EufTSz4w5Qxn4czQ25IzznvTsnVLIHG/dHKHxSdJopcjvJD3FGEFCpkDvGE9XfmYpcuGPoxSQBlUq5g2glRAkn3EG0qu5c6Mhduq3KG2+GO4hOnyqg2nJH0aCZKzIJdxSNG1lCnzuKxpQsodTNU5stxGIb7igaF7KER+4oGm9kCU/cUTSOSGhszB1F4/V76YYsodSRZkmW8I07ikaPLKHUg7aQLOGUO4rGmSzhjTuKxpYsodjbYGQJuYNoUS29pU4WNDveGakDTaczIEoo+CSYZt0mdVWaoemmcjspVTeVutP2F8XCTe5+cIbiIQbcIZ5zf4hSV905933vAXeEMq7Dqegz7rtPp4CS58Kc2xuG8GHmzuVFWOqBxQP7m21r7qabst2Sknpc8ZtntwI/Sb5I8yA+WQRctShgx2Z3+Ohxt7miqpeHLm0LWPXCfmuu6f9U5eKC1KsJJVLTWeMifrWtlRh9oCd1h9uINyrNN2zXJFHg6ZfA10X7htACs15xZ91FYs8nKusHi8dRZzkKWt89H3nBLfQz4S14ib4JAAAAAAAAAC8n7qfpdjYJ/dGdH05m2zTtt7ra3rdtkIyi5al4r+06XkbTW7Bt66ZNkHxszAoQrDbdRPCFyyLxeVr9iHQ8TNqxvZgmXZsD4O+U3ZvwQ5pg4f4N4mYqtsfOorJapaaua3mVhuIz3SdBd+uzpLlkHhEU3ikIOZMxj2wtxk1T4yH/jegb3WeVxT5Dzgc5sC2QWM0H14MMaOrtmDhwTCAB3df3JjZNZ2w4X+MZU+rJz0zU2IrOLy6T34BmKkYP6p4fnjk2MKzSfc5sp/YqWTy/wJ/qvQse05VNsPdW44tySlbMy8m1tjE1pXr/c7WrKSJJYUsaNV16b34Zo1fLlxnlN0WbVEMtXrqSEDToV6n1vcjbWVEHpCrcSYe6Uq2ccTS3pw3oWmm9DrR7qvzL0d9IF6ixvE5KPO1TFS2hRfmuSFcBihLlaCprPZOjXNdQFXmmRflFX5c7TCEkREIk5IeESIiE/JAQCZGQHxIiIRLyQ8IqJG6XKtUjTBj2uvL0JP/HHgAAAAAAAAAAAAAAAAAAAPyf/gCZuUm9oVCsnAAAAABJRU5ErkJggg==",
    //       },
    //       {
    //         text: datajson.message,
    //         timeSent: new Date(),
    //         side: MessageSide.Right,
    //         icon: crow,
    //       },
    //     ]);
    //   })
    // );
  };

  // const getPersonalities = async () => {
  //   // setPersonalities(["RWKV"]);
  //   const data = await fetch(server + "/personalities.json");
  //   const datajson = await data.json();
  //   setPersonalities(datajson);
  // };

  // Should be called on once everythings loaded
  // useEffect(() => {
  //   if (personalities.length === 0) {
  //     getPersonalities();
  //   }
  // });

  const onInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setCurrentMessage(event.target.value);
  };

  const onSend = () => {
    setMessages([
      ...messages,
      {
        text: currentMessage,
        timeSent: new Date(),
        icon: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAOEAAADhCAMAAAAJbSJIAAAAeFBMVEX///8AAACAgIB8fHz19fXp6emNjY37+/umpqbY2NiYmJiwsLB2dnb4+PgwMDCtra2UlJTKysq/v7/R0dGdnZ1eXl4qKipvb2/v7+9ISEhRUVHg4OATExMLCwsiIiJnZ2eIiIhBQUE6OjrDw8NFRUVZWVkbGxu4uLjqLqXEAAAEJElEQVR4nO3di3aiMBAGYOMNEPCCN6pWq1Z9/zfcspazPZZISAZmcP/vCfIfYhKSMHY6AAAAAAAAAAAAAAAAAAAAAK+nPwhCf5jxJ8Ggz90cYvF8sVypn1aX0fx1Us6jnSryvp5xN42CNylMl/Nj7gY68vz904BK7Ratzjgfl+TL7M/czbTmrQ3yZQ4tHXOCq2HAL3Puxtp4PsI8WnA3t7qPSgGVirgbXJXpT/CfJXeTqzlUDtiyiJFFwK8hlbvZ5oZWAZXqcjfclG8ZUKkRd9PNBNYBWzIveiYrNZ19G1Y3dqNMrgWjzdwpoFLyl+EufTSz4w5Qxn4czQ25IzznvTsnVLIHG/dHKHxSdJopcjvJD3FGEFCpkDvGE9XfmYpcuGPoxSQBlUq5g2glRAkn3EG0qu5c6Mhduq3KG2+GO4hOnyqg2nJH0aCZKzIJdxSNG1lCnzuKxpQsodTNU5stxGIb7igaF7KER+4oGm9kCU/cUTSOSGhszB1F4/V76YYsodSRZkmW8I07ikaPLKHUg7aQLOGUO4rGmSzhjTuKxpYsodjbYGQJuYNoUS29pU4WNDveGakDTaczIEoo+CSYZt0mdVWaoemmcjspVTeVutP2F8XCTe5+cIbiIQbcIZ5zf4hSV905933vAXeEMq7Dqegz7rtPp4CS58Kc2xuG8GHmzuVFWOqBxQP7m21r7qabst2Sknpc8ZtntwI/Sb5I8yA+WQRctShgx2Z3+Ohxt7miqpeHLm0LWPXCfmuu6f9U5eKC1KsJJVLTWeMifrWtlRh9oCd1h9uINyrNN2zXJFHg6ZfA10X7htACs15xZ91FYs8nKusHi8dRZzkKWt89H3nBLfQz4S14ib4JAAAAAAAAAC8n7qfpdjYJ/dGdH05m2zTtt7ra3rdtkIyi5al4r+06XkbTW7Bt66ZNkHxszAoQrDbdRPCFyyLxeVr9iHQ8TNqxvZgmXZsD4O+U3ZvwQ5pg4f4N4mYqtsfOorJapaaua3mVhuIz3SdBd+uzpLlkHhEU3ikIOZMxj2wtxk1T4yH/jegb3WeVxT5Dzgc5sC2QWM0H14MMaOrtmDhwTCAB3df3JjZNZ2w4X+MZU+rJz0zU2IrOLy6T34BmKkYP6p4fnjk2MKzSfc5sp/YqWTy/wJ/qvQse05VNsPdW44tySlbMy8m1tjE1pXr/c7WrKSJJYUsaNV16b34Zo1fLlxnlN0WbVEMtXrqSEDToV6n1vcjbWVEHpCrcSYe6Uq2ccTS3pw3oWmm9DrR7qvzL0d9IF6ixvE5KPO1TFS2hRfmuSFcBihLlaCprPZOjXNdQFXmmRflFX5c7TCEkREIk5IeESIiE/JAQCZGQHxIiIRLyQ8IqJG6XKtUjTBj2uvL0JP/HHgAAAAAAAAAAAAAAAAAAAPyf/gCZuUm9oVCsnAAAAABJRU5ErkJggg==",
      },
      {
        text: "RWKV is typing...",
        side: MessageSide.Right,
      },
    ]);
    getMessage(currentMessage, state);
    setCurrentMessage("");
  };

  // const onCharacterChange = (event: SelectChangeEvent<{ value: string }>) => {
  //   setCharacter(event.target.value as string);
  //   setMessages([]);
  //   setState(undefined);
  // };

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Nav
        server={server}
        setServer={setServer}
        darkmode={darkmode}
        setDarkmode={setDarkmode}
        messages={messages}
        setMessages={setMessages}
        state={state}
        setState={setState}
      />
      <div className="App">
        <br></br>

        <div className="message-box">
          <TextField
            id="outlined-basic"
            multiline
            label="Message"
            variant="outlined"
            className="message-input"
            fullWidth
            value={currentMessage}
            onChange={onInputChange}
            color="primary"
            InputProps={{
              endAdornment: (
                <Button variant="contained" onClick={onSend}>
                  Send
                </Button>
              ),
            }}
            // on enter press
            onKeyDown={(event) => {
              if (event.key === "Enter" && event.shiftKey === false) {
                onSend();
              }
            }}
          />
          {messages
            .map((message, index) => (
              <Message
                key={index}
                {...{ ...message, index: messages.length - index }}
                darkTheme={darkmode}
              />
            ))
            .reverse()}
        </div>
      </div>
    </ThemeProvider>
  );
}

export default App;
