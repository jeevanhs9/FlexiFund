import { useEffect } from 'react';

/**
 * React hook to add scroll-based animations to elements
 * Usage: useScrollAnimations() in your component
 */
export function useScrollAnimations() {
  useEffect(() => {
    const observerOptions = {
      threshold: 0.1,
      rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('animate-in');
        }
      });
    }, observerOptions);

    // Observe all animated elements
    const animatedElements = document.querySelectorAll(
      '.scroll-fade, .scroll-slide-up, .scroll-slide-left, .scroll-slide-right, ' +
      '.scroll-scale, .scroll-rotate, .scroll-blur, .scroll-flip, ' +
      '.scroll-bounce, .scroll-wave, .scroll-zoom, .scroll-elastic, .scroll-glow'
    );

    animatedElements.forEach(el => observer.observe(el));

    // Add topbar scroll effect
    const topbar = document.querySelector('.topbar');
    const handleScroll = () => {
      if (window.scrollY > 50) {
        topbar?.classList.add('scrolled');
      } else {
        topbar?.classList.remove('scrolled');
      }
    };

    window.addEventListener('scroll', handleScroll);

    // Cleanup
    return () => {
      animatedElements.forEach(el => observer.unobserve(el));
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);
}

/**
 * Hook to add parallax effect to elements
 */
export function useParallax(speed = 0.5) {
  useEffect(() => {
    let ticking = false;

    const handleScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          const scrolled = window.pageYOffset;
          const parallaxElements = document.querySelectorAll('.parallax');
          
          parallaxElements.forEach(element => {
            const elementSpeed = parseFloat(element.dataset.parallaxSpeed) || speed;
            const yPos = -(scrolled * elementSpeed);
            element.style.transform = `translate3d(0, ${yPos}px, 0)`;
          });

          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', handleScroll);

    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, [speed]);
}

/**
 * Hook to add scroll progress bar
 */
export function useScrollProgress() {
  useEffect(() => {
    const handleScroll = () => {
      const winScroll = document.documentElement.scrollTop;
      const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      const scrolled = (winScroll / height) * 100;
      
      const progressBar = document.querySelector('.scroll-progress-bar');
      if (progressBar) {
        progressBar.style.width = scrolled + '%';
      }
    };

    window.addEventListener('scroll', handleScroll);

    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);
}
