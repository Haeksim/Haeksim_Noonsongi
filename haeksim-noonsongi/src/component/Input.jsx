import React, { useRef, useEffect } from "react";
import styles from "./Input.module.css";
import add from "../icon/add.png";

export default function Input() {
  const textareaRef = useRef(null);

  const handleInput = () => {
    const textarea = textareaRef.current;
    textarea.style.height = "auto"; // reset height
    const maxHeight = 200; // max height in px
    textarea.style.height = Math.min(textarea.scrollHeight, maxHeight) + "px";
  };

  useEffect(() => {
    handleInput();
  }, []);
  return (
    <div className={styles.inputContainer}>
      <div className={styles.input}>
        <textarea
          ref={textareaRef}
          placeholder="정리할 것을 입력해보세요"
          className={styles.textarea}
          onInput={handleInput}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
            }
          }}
          rows={1}
        ></textarea>
        <img src={add} className={styles.attAddBtn} />
      </div>
      <p className={styles.warning}>
        Haeksim은 실수를 할 수 있습니다. 중요한 정보는 재차 확인하세요.
      </p>
    </div>
  );
}
