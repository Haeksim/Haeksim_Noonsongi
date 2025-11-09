import React, { useContext } from "react";

import PayloadContext from "../context/PayloadContext";
import styles from "./SearchBody.module.css";

export default function SearchBody() {
  const { prompt, setPrompt, payload, setPayload } = useContext(PayloadContext);
  return (
    <div>
      <div className={styles.questionContainer}>
        <div className={styles.question}>
          <p>{prompt}</p>
        </div>
      </div>
    </div>
  );
}
