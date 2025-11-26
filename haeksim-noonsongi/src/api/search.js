import { defaultAxios } from "../axios";

export const postSearch = async (payload) => {
  console.log("post");
  console.log(payload);

  if (!payload.prompt || !payload.file) return;

  const formData = new FormData();
  formData.append("prompt", payload.prompt);
  formData.append("file", payload.file);

  const response = await defaultAxios.post("/api/generate", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

  return response.data.task_id;
};

export const getSearchResult = async (taskId) => {
  console.log("get");
  const response = await defaultAxios.get(`/api/status/${taskId}`);
  return response;
};
