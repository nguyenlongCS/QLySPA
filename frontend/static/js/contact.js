document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('.contact-form');
  if (!form) return;

  /* ================= CONFIG ================= */

  const phoneRegex = /^(?=.*\d)[0-9\s]+$/;

  const allowedDomains = [
    'gmail.com',
    'yahoo.com',
    'outlook.com',
    'hotmail.com',
    'icloud.com',
    'live.com',
    'proton.me',
    'protonmail.com'
  ];

  const isValidEmail = email => {
    const parts = email.toLowerCase().split('@');
    return parts.length === 2 && allowedDomains.includes(parts[1]);
  };

  const phoneInput = form.querySelector('input[name="phone"]');
  if (phoneInput) {
    phoneInput.addEventListener('input', () => {
      phoneInput.value = phoneInput.value.replace(/[^0-9\s]/g, '');
    });
  }

  /* ================= SUBMIT ================= */
  form.addEventListener('submit', e => {
    e.preventDefault();
    let valid = true;

    form.querySelectorAll('.form-group').forEach(group => {
      group.classList.remove('error');
      group.removeAttribute('data-error');
    });

    form.querySelectorAll('input, textarea').forEach(input => {
      const group = input.closest('.form-group');
      if (!group) return;

      const value = input.value.trim();

      if (input.tagName === 'TEXTAREA') return;

      if (!value) {
        group.dataset.error = 'Vui lòng điền vào trường này.';
        group.classList.add('error');
        valid = false;
        return;
      }

      if (input.name === 'phone') {
        if (!phoneRegex.test(value)) {
          group.dataset.error =
            'SĐT chỉ được chứa chữ số, không được toàn dấu cách';
          group.classList.add('error');
          valid = false;
        }
      }

      if (input.name === 'email') {
        if (!isValidEmail(value)) {
          group.dataset.error =
            'Vui lòng bao gồm @ trong địa chỉ email';
          group.classList.add('error');
          valid = false;
        }
      }
    });

    if (valid) {
      const success = form.querySelector('.success');
      if (success) {
        success.style.display = 'block';
      } else {
        alert('Gửi thành công!');
      }
      form.reset();
    }
  });
});

// Chỉ chạy parallax effect nếu element tồn tại
window.addEventListener("scroll", () => {
    const img = document.querySelector(".contact-image-text1 img");
    if (img) {
        const offset = window.scrollY * 0.3;
        img.style.transform = `translateY(${offset}px)`;
    }
});