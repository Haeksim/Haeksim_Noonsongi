import React from "react";
import styles from "./Body.module.css";

import StartBody from "./StartBody";

export default function Body() {
  return (
    <div className={styles.body}>
      <StartBody />
    </div>
  );
}
