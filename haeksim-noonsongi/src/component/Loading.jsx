import React from "react";
import loadingImg from "../icon/loading.png";
import styles from "./Loading.module.css";

export default function Loading() {
  return (
    <div>
      <img src={loadingImg} className={styles.img} />
    </div>
  );
}
