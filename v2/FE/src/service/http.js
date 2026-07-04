//http.js
import axios from "axios";
import NProgress from "nprogress";
import { ElMessage } from "element-plus";
import { checkStatus } from "./checkStatus";

// 设置请求头和请求路径
axios.defaults.baseURL = "/api";
axios.defaults.timeout = 60000; // 超时时间 60秒

// 响应拦截:data 是后端统一信封 { status, code, message, data, timestamp }
axios.interceptors.response.use(
  (response) => {
    const { data } = response;
    // 业务失败判定:信封内 status 非 200
    if (data.status && data.status !== 200) {
      ElMessage.error(data.message || "获取接口错误");
      return Promise.reject(data);
    }
    // 成功:解出信封里的业务数据,业务层无需关心信封结构
    return data.data;
  },
  (error) => {
    // 根据 HTTP 状态码做统一错误提示
    const { response } = error;
    if (response) checkStatus(response.status, response.data?.message);
    return Promise.reject(error);
  },
);

const http = {
  get(url, params, config = {}) {
    return new Promise((resolve, reject) => {
      NProgress.start();
      axios
        .get(url, { params, ...config })
        .then((res) => {
          NProgress.done();
          resolve(res);
        })
        .catch((err) => {
          NProgress.done();
          reject(err?.data || err?.response?.data || err);
        });
    });
  },
  post(url, params, config = {}) {
    // 非 FormData 时默认 JSON 请求头(FormData 由浏览器自动设置 boundary)
    if (!(params instanceof FormData)) {
      config = {
        headers: { "Content-Type": "application/json;charset=UTF-8" },
        ...config,
      };
    }
    return new Promise((resolve, reject) => {
      NProgress.start();
      axios
        .post(url, params, { ...config })
        .then((res) => {
          NProgress.done();
          resolve(res);
        })
        .catch((err) => {
          NProgress.done();
          reject(err.data);
        });
    });
  },
  put(url, params) {
    return new Promise((resolve, reject) => {
      NProgress.start();
      axios
        .put(url, params)
        .then((res) => {
          NProgress.done();
          resolve(res);
        })
        .catch((err) => {
          NProgress.done();
          reject(err.data);
        });
    });
  },
  upload(url, file) {
    return new Promise((resolve, reject) => {
      NProgress.start();
      axios
        .post(url, file, {
          headers: { "Content-Type": "multipart/form-data" },
        })
        .then((res) => {
          NProgress.done();
          resolve(res);
        })
        .catch((err) => {
          NProgress.done();
          reject(err.data);
        });
    });
  },
  delete(url, params, config = {}) {
    return new Promise((resolve, reject) => {
      NProgress.start();
      axios
        .delete(url, { params, ...config })
        .then((res) => {
          NProgress.done();
          resolve(res);
        })
        .catch((err) => {
          NProgress.done();
          reject(err.data);
        });
    });
  },
};
export default http;
