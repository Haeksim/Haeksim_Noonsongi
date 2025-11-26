import axios from "axios";

const defaultAxios = axios.create({
  baseURL: "https://haeksimnoonsongi-production-9a31.up.railway.app/",
  headers: {
    "Content-Type": "application/json",
  },
});
export { defaultAxios };
