/**
 * AVALON MOTORS — Main JavaScript
 * Global UI interactions, navbar scroll effect, sidebar toggle
 */

'use strict';

// ─── Navbar Scroll Effect ───────────────────────────────────────────
window.addEventListener('scroll', () => {
  const nav = document.querySelector('.avalon-nav');
  if (nav) {
    if (window.scrollY > 60) {
      nav.classList.add('scrolled');
    } else {
      nav.classList.remove('scrolled');
    }
  }
}, { passive: true });

// ─── Sidebar Toggle (Mobile) ────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('sidebar');

  // Create toggle button for mobile
  if (sidebar) {
    const toggleBtn = document.createElement('button');
    toggleBtn.id = 'sidebarToggle';
    toggleBtn.innerHTML = '<i class="bi bi-layout-sidebar-inset"></i>';
    toggleBtn.style.cssText = `
      position: fixed; bottom: 1.5rem; right: 1.5rem;
      z-index: 200; width: 48px; height: 48px;
      background: var(--electric); border: none;
      border-radius: 50%; color: white;
      font-size: 1.2rem; cursor: pointer;
      box-shadow: 0 4px 20px rgba(0,102,255,0.5);
      display: none; align-items: center; justify-content: center;
      transition: var(--transition);
    `;

    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });

    document.body.appendChild(toggleBtn);

    const mq = window.matchMedia('(max-width: 991.98px)');
    const handleMQ = (e) => {
      toggleBtn.style.display = e.matches ? 'flex' : 'none';
    };
    mq.addListener(handleMQ);
    handleMQ(mq);

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
      if (window.innerWidth < 992) {
        if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
          sidebar.classList.remove('open');
        }
      }
    });
  }

  // ─── Active nav link highlight ───────────────────────────────────
  const currentPath = window.location.pathname;
  document.querySelectorAll('.avalon-nav-link').forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.style.color = 'var(--cyan)';
    }
  });

  // ─── Animate stat counters ───────────────────────────────────────
  const counters = document.querySelectorAll('.stat-value[data-count]');
  counters.forEach(counter => {
    const target = parseInt(counter.dataset.count, 10);
    const duration = 1200;
    const step = target / (duration / 16);
    let current = 0;

    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      counter.textContent = Math.floor(current);
      if (current >= target) clearInterval(timer);
    }, 16);
  });

  // ─── Tooltip init (Bootstrap) ────────────────────────────────────
  const tooltipEls = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipEls.forEach(el => new bootstrap.Tooltip(el));

  // ─── Confirmation dialogs for destructive actions ────────────────
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', (e) => {
      if (!confirm(el.dataset.confirm)) {
        e.preventDefault();
      }
    });
  });

  // ─── Auto-hide alerts after 5s ──────────────────────────────────
  document.querySelectorAll('.alert-dismissible').forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

});

// ─── Particle Background (for auth pages) ─────────────────────────
function initParticles(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  canvas.width  = window.innerWidth;
  canvas.height = window.innerHeight;

  const particles = Array.from({ length: 60 }, () => ({
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height,
    r: Math.random() * 2 + 0.5,
    dx: (Math.random() - 0.5) * 0.4,
    dy: (Math.random() - 0.5) * 0.4,
    opacity: Math.random() * 0.5 + 0.1,
  }));

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0, 212, 255, ${p.opacity})`;
      ctx.fill();

      p.x += p.dx;
      p.y += p.dy;
      if (p.x < 0 || p.x > canvas.width)  p.dx *= -1;
      if (p.y < 0 || p.y > canvas.height) p.dy *= -1;
    });

    // Draw connecting lines
    particles.forEach((a, i) => {
      particles.slice(i + 1).forEach(b => {
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < 120) {
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = `rgba(0, 212, 255, ${0.06 * (1 - d / 120)})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      });
    });

    requestAnimationFrame(draw);
  }

  draw();

  window.addEventListener('resize', () => {
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
  }, { passive: true });
}

// ─── Format Duration Helper ────────────────────────────────────────
function formatDuration(seconds) {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m < 60) return `${m}m ${s}s`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}

// ─── Copy to Clipboard ─────────────────────────────────────────────
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('Copied to clipboard!', 'success');
  });
}

// ─── Mini Toast ────────────────────────────────────────────────────
function showToast(message, type = 'info') {
  let container = document.getElementById('avalonMessages');
  if (!container) {
    container = document.createElement('div');
    container.className = 'avalon-messages';
    container.id = 'avalonMessages';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `avalon-toast avalon-toast-${type}`;
  const icons = { success: 'check-circle-fill', error: 'x-circle-fill', warning: 'exclamation-triangle-fill', info: 'info-circle-fill' };
  toast.innerHTML = `
    <div class="toast-icon"><i class="bi bi-${icons[type] || icons.info}"></i></div>
    <span>${message}</span>
    <button onclick="this.parentElement.remove()" class="toast-close"><i class="bi bi-x"></i></button>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'slideOutRight 0.4s ease forwards';
    setTimeout(() => toast.remove(), 400);
  }, 4000);
}
