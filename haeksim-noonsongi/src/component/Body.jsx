import React, { useContext } from "react";
import styles from "./Body.module.css";

import PayloadContext from "../context/PayloadContext";
import StartBody from "./StartBody";
import SearchBody from "./SearchBody";

export default function Body() {
  const { payload } = useContext(PayloadContext);
  return (
    <div className={styles.body}>
      {payload.file && payload.prompt ? <SearchBody /> : <StartBody />}
    </div>
  );
}
