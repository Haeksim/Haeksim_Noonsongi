import { defaultAxios } from "../axios";

export const postSearch = async (payload) => {
  console.log("post");
  const response = await defaultAxios.post("/api/generate", {
    ...payload,
  });
  return response.data?.task_id;
};

export const getSearchResult = async (taskId) => {
  console.log("get");
  const response = await defaultAxios.get(`/api/status/${taskId}`);
  return response;
};
