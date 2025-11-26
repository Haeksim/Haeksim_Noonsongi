import React, { useState, useRef, useEffect, useContext } from "react";
import PayloadContext from "../context/PayloadContext";
import { postSearch, getSearchResult } from "../api/search";

import styles from "./Input.module.css";
import add from "../icon/add.png";

export default function Input() {
  const [input, setInput] = useState("");
  const { prompt, setPrompt, payload, setPayload, result, setResult } =
    useContext(PayloadContext);
  const textareaRef = useRef(null);

  //인풋 상자 크기 조정 로직
  const handleInputBox = () => {
    const textarea = textareaRef.current;
    textarea.style.height = "auto";
    const maxHeight = 200;

    if (textarea.value === "") {
      textarea.style.height = textarea + "px";
      return;
    }

    textarea.style.height = Math.min(textarea.scrollHeight, maxHeight) + "px";
  };

  //text 입력 로직
  const handleInput = (e) => {
    setInput(e.target.value);
  };

  //pdf 파일 입력 로직
  const handleFileInput = () => {
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = ".pdf";
    fileInput.addEventListener("change", (event) => {
      const file = event.target.files[0];
      if (file) {
        setPrompt(file.name);
        setPayload({ prompt: "", file: file });
      }
    });
    fileInput.click();
  };

  //폴링 기다리기
  function pollStatus(taskId) {
    return new Promise((resolve, reject) => {
      const interval = setInterval(async () => {
        try {
          const res = await getSearchResult(taskId);
          const status = res.data.status;

          if (status === "completed") {
            clearInterval(interval);
            resolve(res.data.result); // return the result properly
          } else if (status === "failed") {
            clearInterval(interval);
            reject(res.data.error); // reject if failed
          } else {
            console.log("생성 중... (현재 상태: " + status + ")");
          }
        } catch (err) {
          clearInterval(interval);
          reject(err);
        }
      }, 4000);
    });
  }

  useEffect(() => {
    handleInputBox();
  }, [input]);
  return (
    <div className={styles.inputContainer}>
      <div className={styles.input}>
        <textarea
          rows={1}
          ref={textareaRef}
          placeholder="정리할 것을 입력해보세요"
          value={input}
          onChange={handleInput}
          onInput={handleInputBox}
          onKeyDown={async (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              setPrompt(input);
              setPayload({ prompt: input, file: "" });
              setInput("");
              const taskId = await postSearch(payload);
              console.log(taskId);
              const result = await pollStatus(taskId);
              setResult(result);
            }
          }}
          className={styles.textarea}
        ></textarea>
        <img src={add} className={styles.attAddBtn} onClick={handleFileInput} />
      </div>
      <p className={styles.warning}>
        Haeksim은 실수를 할 수 있습니다. 중요한 정보는 재차 확인하세요.
      </p>
    </div>
  );
}
