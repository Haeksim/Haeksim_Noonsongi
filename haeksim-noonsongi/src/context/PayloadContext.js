import { createContext, useState } from "react";

const PayloadContext = createContext();

export function PayloadProvider({ children }) {
  //화면에 보일 프롬프트
  const [prompt, setPrompt] = useState("");
  //모듈에 넘겨질 오브젝트
  const [payload, setPayload] = useState({ text: "", pdf: null });
  return (
    <PayloadContext.Provider value={{ prompt, setPrompt, payload, setPayload }}>
      {children}
    </PayloadContext.Provider>
  );
}
export default PayloadContext;
