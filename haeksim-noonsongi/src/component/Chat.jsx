import React from "react";
import styles from "./Chat.module.css";

export default function Chat({ children, owner }) {
  return (
    <div>
      <div className={styles[owner]}>
        <div className={styles.chat}>{children}</div>
      </div>
    </div>
  );
}
