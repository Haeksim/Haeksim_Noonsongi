import React, { useContext } from "react";
import styles from "./Body.module.css";

import PayloadContext from "../context/PayloadContext";
import StartBody from "./StartBody";
import SearchBody from "./SearchBody";

export default function Body() {
  const { prompt } = useContext(PayloadContext);
  return (
    <div className={styles.body}>{prompt ? <SearchBody /> : <StartBody />}</div>
  );
}
