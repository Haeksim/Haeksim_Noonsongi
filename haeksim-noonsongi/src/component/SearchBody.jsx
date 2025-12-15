import React, { useContext, useEffect } from "react";
import Chat from "./Chat";
import Loading from "./Loading";

import PayloadContext from "../context/PayloadContext";
import styles from "./SearchBody.module.css";

export default function SearchBody() {
  const { payload, setPayload, result, setResult } = useContext(PayloadContext);
  useEffect(() => {
    console.log(result);
  }, [result]);
  return (
    <div>
      <Chat owner={"user"}>
        <p>{`${payload.file.name} \n ${payload.prompt}`}</p>
      </Chat>
      <Chat owner={"ai"}>
        <div className={styles.videoContainer}>
          {result ? (
            <video src={result} controls className={styles.video} />
          ) : (
            <Loading />
          )}
        </div>
      </Chat>
    </div>
  );
}
