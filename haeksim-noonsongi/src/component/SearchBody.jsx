import React, { useContext } from "react";
import Chat from "./Chat";

import PayloadContext from "../context/PayloadContext";
import styles from "./SearchBody.module.css";

export default function SearchBody() {
  const { prompt, setPrompt, payload, setPayload, result, setResult } =
    useContext(PayloadContext);
  return (
    <div>
      <Chat owner={"user"}>
        <p>{prompt}</p>
      </Chat>
      {result && (
        <Chat owner={"ai"}>
          <div className={styles.videoContainer}>
            <video src={result} controls className={styles.video} />
          </div>
        </Chat>
      )}
    </div>
  );
}
