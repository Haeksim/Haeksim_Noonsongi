import React, { useState, useRef, useEffect, useContext } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import PayloadContext from "../context/PayloadContext";
import { postSearch, getSearchResult } from "../api/search";

import styles from "./Input.module.css";
import add from "../icon/add.png";

export default function Input() {
  const [input, setInput] = useState("");
  const { payload, setPayload, result, setResult } = useContext(PayloadContext);
  const textareaRef = useRef(null);

  //API 관련 코드
  const startSearchMutation = useMutation({
    mutationFn: postSearch,
  });
  const {
    data: searchData,
    isLoading: isPolling,
    isError,
    error,
  } = useQuery({
    queryKey: ["searchResult", startSearchMutation.data],
    queryFn: () => getSearchResult(startSearchMutation.data),
    enabled: !!startSearchMutation.data,
    refetchInterval: (query) => {
      const status = query.state.data?.data?.status;

      if (status === "completed" || status === "failed") {
        return false; // stop polling
      }
      return 4000; // poll every 4 seconds
    },
  });
  useEffect(() => {
    const status = searchData?.data?.status;

    if (status === "completed") {
      setResult(searchData.data.result);
    }

    if (status === "failed") {
      alert(searchData.data.error);
    }
  }, [searchData]);

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
        setPayload((prev) => ({ ...prev, file: file }));
      }
    });
    fileInput.click();
  };

  const handleEnter = async (e) => {
    const nextPayload = {
      ...payload,
      prompt: input,
    };

    setPayload(nextPayload);
    setInput("");

    startSearchMutation.mutate(nextPayload);
  };

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
