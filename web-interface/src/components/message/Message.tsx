import "./message.scss";
import React from "react";
import { Avatar, Paper } from "@mui/material";

export enum MessageType {
  Normal = "normal",
  Success = "success",
  Error = "error",
  Info = "info",
  Warning = "warning",
}

export enum MessageSide {
  Left = "left",
  Right = "right",
}

export interface MessageProps {
  text?: string;
  icon?: string;
  type?: MessageType;
  side?: MessageSide;
  index?: number;
}

function Message({
  text = "No message",
  type = MessageType.Normal,
  side = MessageSide.Left,
  icon = undefined,
  index = 10,
}: MessageProps) {
  return (
    <Paper
      elevation={Math.max(12 - index, 0)}
      className={["message", type, side].join(" ")}
      sx={{
        position: "relative",
      }}
    >
      {icon ? (
        <Avatar
          src={icon}
          alt="icon"
          sx={{
            width: 32,
            height: 32,
            position: "absolute",
            top: -16,
            filter: "invert(1)",
            ...(side === MessageSide.Left ? { left: -16 } : { right: -16 }),
          }}
        />
      ) : (
        ""
      )}
      {text}
    </Paper>
  );
}

export default Message;
