import { createContext, useState } from "react";

const PayloadContext = createContext();

export function PayloadProvider({ children }) {
  //화면에 보일 프롬프트
  const [prompt, setPrompt] = useState("");
  //모듈에 넘겨질 오브젝트
  const [payload, setPayload] = useState({ prompt: "", file: null });
  //답장
  const [result, setResult] = useState();
  return (
    <PayloadContext.Provider
      value={{ prompt, setPrompt, payload, setPayload, result, setResult }}
    >
      {children}
    </PayloadContext.Provider>
  );
}
export default PayloadContext;
