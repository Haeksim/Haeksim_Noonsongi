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
        setPayload((prev) => ({ ...prev, file: file }));
      }
    });
    fileInput.click();
  };

  const handleEnter = async (e) => {
    try {
      const nextPayload = {
        ...payload,
        prompt: e.target.value,
      };

      setPrompt(input);
      setPayload(nextPayload);
      setInput("");

      const taskId = await postSearch(nextPayload);
      console.log(taskId);

      if (taskId) {
        const result = await pollStatus(taskId);
        console.log(result);
        setResult(result);
      }
    } catch (e) {
      alert(e);
    }
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
      <div className={styles.attachmentTab}>
        <p>{payload.file?.name}</p>
      </div>
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
              await handleEnter(e);
            }
          }}
          className={styles.textarea}
        ></textarea>
        <img src={add} className={styles.attAddBtn} onClick={handleFileInput} />
      </div>
      <p className={styles.warning}>
        입력된 데이터는 AI 학습 목적으로 활용되지 않습니다. 개인정보 보호 원칙을
        철저히 준수합니다.
      </p>
    </div>
  );
}
