module.exports = function handler(_request, response) {
  response.setHeader("Cache-Control", "no-store");
  response.status(200).json({
    apiBaseUrl: (process.env.API_BASE_URL || "").replace(/\/+$/, ""),
  });
};
