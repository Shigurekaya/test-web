(() => {
  // 登录页演示账号一键填入
  document.querySelectorAll("[data-demo-user]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const user = btn.getAttribute("data-demo-user") || "";
      const pass = btn.getAttribute("data-demo-pass") || "";
      const u = document.querySelector('input[name="username"]');
      const p = document.querySelector('input[name="password"]');
      if (u) u.value = user;
      if (p) p.value = pass;
      u?.focus();
    });
  });

  // Flash 自动收起
  document.querySelectorAll(".alert-dismissible").forEach((el) => {
    setTimeout(() => {
      el.classList.remove("show");
      el.addEventListener("transitionend", () => el.remove(), { once: true });
    }, 4200);
  });
})();
