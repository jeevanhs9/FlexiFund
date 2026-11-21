/**
 * Scroll-based animations using Intersection Observer API
 * Makes elements animate smoothly as they come into view while scrolling
 */

export function initScrollAnimations() {
  // Configuration for different animation types
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  // Create intersection observer for fade-in animations
  const fadeObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate-in');
        // Optional: unobserve after animation to improve performance
        // fadeObserver.unobserve(entry.target);
      } else {
        // Re-animate when scrolling back
        entry.target.classList.remove('animate-in');
      }
    });
  }, observerOptions);

  // Create observer for parallax elements
  const parallaxObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const speed = entry.target.dataset.parallaxSpeed || 0.5;
        const rect = entry.target.getBoundingClientRect();
        const scrolled = window.pageYOffset || document.documentElement.scrollTop;
        const offset = (rect.top + scrolled) - (window.innerHeight / 2);
        const parallax = (scrolled - offset) * speed;
        entry.target.style.transform = `translateY(${parallax}px)`;
      }
    });
  }, { threshold: 0 });

  // Observe all elements with scroll animation classes
  const animateElements = document.querySelectorAll(
    '.scroll-fade, .scroll-slide-up, .scroll-slide-left, .scroll-slide-right, .scroll-scale, .scroll-rotate'
  );
  
  animateElements.forEach(el => {
    fadeObserver.observe(el);
  });

  // Observe parallax elements
  const parallaxElements = document.querySelectorAll('.parallax');
  parallaxElements.forEach(el => {
    parallaxObserver.observe(el);
  });

  // Add scroll progress indicator
  window.addEventListener('scroll', () => {
    const winScroll = document.documentElement.scrollTop;
    const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    const scrolled = (winScroll / height) * 100;
    
    const progressBar = document.querySelector('.scroll-progress-bar');
    if (progressBar) {
      progressBar.style.width = scrolled + '%';
    }
  });

  // Parallax scroll effect for background elements
  let ticking = false;
  window.addEventListener('scroll', () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        updateParallaxElements();
        ticking = false;
      });
      ticking = true;
    }
  });
}

function updateParallaxElements() {
  const scrolled = window.pageYOffset;
  const parallaxElements = document.querySelectorAll('.parallax');
  
  parallaxElements.forEach(element => {
    const speed = parseFloat(element.dataset.parallaxSpeed) || 0.5;
    const yPos = -(scrolled * speed);
    element.style.transform = `translate3d(0, ${yPos}px, 0)`;
  });
}

// Re-initialize when page content changes (for SPA navigation)
export function refreshScrollAnimations() {
  // Small delay to let DOM update
  setTimeout(() => {
    initScrollAnimations();
  }, 100);
}

// Smooth scroll to element
export function scrollToElement(selector, offset = 0) {
  const element = document.querySelector(selector);
  if (element) {
    const elementPosition = element.getBoundingClientRect().top + window.pageYOffset;
    const offsetPosition = elementPosition - offset;

    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    });
  }
}

// Add stagger delay to child elements
export function addStaggerAnimation(parentSelector, childSelector, delayIncrement = 0.1) {
  const parent = document.querySelector(parentSelector);
  if (parent) {
    const children = parent.querySelectorAll(childSelector);
    children.forEach((child, index) => {
      child.style.animationDelay = `${index * delayIncrement}s`;
    });
  }
}


/**
 * Chart-specific animation observer
 * Triggers animations for charts when they scroll into view
 */
export function initChartAnimations() {
  const chartContainers = document.querySelectorAll('.p3-chart-scroll');
  
  if (chartContainers.length === 0) return;

  const chartObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate-in');
      }
    });
  }, {
    threshold: 0.15,
    rootMargin: '0px 0px -80px 0px'
  });

  chartContainers.forEach(container => {
    chartObserver.observe(container);
  });

  return () => {
    chartContainers.forEach(container => chartObserver.unobserve(container));
  };
}

// Initialize chart animations when DOM is ready
if (typeof window !== 'undefined') {
  const initCharts = () => {
    initChartAnimations();
    
    // Re-initialize when content changes (for SPA navigation)
    const contentObserver = new MutationObserver(() => {
      initChartAnimations();
    });
    
    contentObserver.observe(document.body, {
      childList: true,
      subtree: true
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCharts);
  } else {
    initCharts();
  }
}
