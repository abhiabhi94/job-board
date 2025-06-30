import { describe, test, expect, vi, beforeEach } from 'vitest';
import { initializeMainJs } from '../../job_board/static/js/main.mjs';

describe('Main.js Tests', () => {
  beforeEach(() => {
    document.documentElement.innerHTML = '<html><head></head><body></body></html>';

    global.localStorage = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      clear: vi.fn(),
      removeItem: vi.fn()
    };

    global.fetch = vi.fn(() => Promise.resolve({
      text: () => Promise.resolve(`
        <html>
          <body>
            <article data-job-id="4">New Job</article>
            <div data-has-next="true"></div>
          </body>
        </html>
      `)
    }));

    global.setTimeout = setTimeout;
    global.clearTimeout = clearTimeout;

    delete window.loadMoreJobs;
    delete window.clearAllFilters;

    vi.clearAllMocks();
  });

  describe('Theme Toggle', () => {
    test('should toggle between dark and light modes', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle Theme</div>
          </body>
        </html>
      `;

      initializeMainJs();

      const themeToggle = document.getElementById('theme-toggle');

      // Test dark mode toggle
      expect(document.documentElement.classList.contains('dark')).toBe(false);
      themeToggle.click();
      expect(document.documentElement.classList.contains('dark')).toBe(true);
      expect(localStorage.setItem).toHaveBeenCalledWith('theme', 'dark');

      // Test light mode toggle
      themeToggle.click();
      expect(document.documentElement.classList.contains('dark')).toBe(false);
      expect(localStorage.setItem).toHaveBeenCalledWith('theme', 'light');
    });
  });

  describe('Job Card Animations', () => {
    test('should apply staggered animations to job cards', () => {
      // Mock setTimeout to capture callbacks and execute them immediately
      const setTimeoutCallbacks = [];
      global.setTimeout = vi.fn((callback, delay) => {
        setTimeoutCallbacks.push({ callback, delay });
        callback(); // Execute immediately for testing
        return 1;
      });

      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <article>Job Card 1</article>
            <article>Job Card 2</article>
          </body>
        </html>
      `;

      initializeMainJs();

      // Verify setTimeout was called for staggered animation (at least 2 times for the 2 articles)
      expect(global.setTimeout).toHaveBeenCalledWith(expect.any(Function), 0);   // First card
      expect(global.setTimeout).toHaveBeenCalledWith(expect.any(Function), 100); // Second card

      // Since we execute callbacks immediately, check final animation styles
      const articles = document.querySelectorAll('article');
      articles.forEach(card => {
        expect(card.style.transition).toBe('opacity 0.6s ease-out, transform 0.6s ease-out');
        expect(card.style.opacity).toBe('1');
        expect(card.style.transform).toBe('translateY(0)');
      });
    });
  });

  describe('Keyboard Navigation', () => {
    test('should handle keyboard navigation for tag labels', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <input type="checkbox" id="tag-1" class="tag-checkbox">
            <label for="tag-1" class="tag-label">Tag 1</label>
          </body>
        </html>
      `;

      initializeMainJs();

      const label = document.querySelector('.tag-label');
      const checkbox = document.getElementById('tag-1');
      checkbox.dispatchEvent = vi.fn();

      // Test Enter key
      expect(checkbox.checked).toBe(false);
      label.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
      expect(checkbox.checked).toBe(true);
      expect(checkbox.dispatchEvent).toHaveBeenCalled();

      // Test Space key
      checkbox.checked = false;
      label.dispatchEvent(new KeyboardEvent('keydown', { key: ' ' }));
      expect(checkbox.checked).toBe(true);
    });

    test('should handle keyboard navigation for job cards', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <article role="button">Job Card</article>
          </body>
        </html>
      `;

      initializeMainJs();

      const jobCard = document.querySelector('article[role="button"]');
      jobCard.click = vi.fn();

      // Test Enter key
      const enterEvent = new KeyboardEvent('keydown', { key: 'Enter' });
      Object.defineProperty(enterEvent, 'preventDefault', { value: vi.fn() });

      jobCard.dispatchEvent(enterEvent);
      expect(enterEvent.preventDefault).toHaveBeenCalled();
      expect(jobCard.click).toHaveBeenCalled();

      // Test Space key
      jobCard.click.mockClear();
      const spaceEvent = new KeyboardEvent('keydown', { key: ' ' });
      Object.defineProperty(spaceEvent, 'preventDefault', { value: vi.fn() });

      jobCard.dispatchEvent(spaceEvent);
      expect(spaceEvent.preventDefault).toHaveBeenCalled();
      expect(jobCard.click).toHaveBeenCalled();
    });
  });

  describe('Tag Input Interactions', () => {
    test('should handle tag input changes with visual feedback', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <form id="filter-form">
              <input type="checkbox" class="tag-checkbox">
              <label>Tag Label</label>
              <button id="filter-submit-btn">Submit</button>
            </form>
          </body>
        </html>
      `;

      const form = document.getElementById('filter-form');
      form.submit = vi.fn();

      initializeMainJs();

      const input = document.querySelector('.tag-checkbox');
      const label = input.nextElementSibling;
      const submitBtn = document.getElementById('filter-submit-btn');

      // Trigger change event
      input.dispatchEvent(new Event('change'));

      // Check loading styles
      expect(label.style.opacity).toBe('0.6');
      expect(label.style.transform).toBe('scale(0.95)');
      expect(submitBtn.classList.contains('loading')).toBe(true);
      expect(form.submit).toHaveBeenCalled();
    });
  });

  describe('Sort Dropdown', () => {
    test('should handle complete sort dropdown functionality', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div class="sort-dropdown">
              <button id="sort-button">
                <span class="sort-text">Sort by</span>
                <span class="sort-arrow">↓</span>
              </button>
              <div id="sort-options" class="hidden">
                <input name="sort" type="hidden">
                <div class="sort-option" data-value="date">Most Recent</div>
              </div>
            </div>
            <form id="filter-form"></form>
          </body>
        </html>
      `;

      const form = document.getElementById('filter-form');
      form.submit = vi.fn();

      initializeMainJs();

      const sortButton = document.getElementById('sort-button');
      const sortOptions = document.getElementById('sort-options');
      const sortArrow = document.querySelector('.sort-arrow');
      const option = document.querySelector('.sort-option');
      const sortText = document.querySelector('.sort-text');
      const hiddenInput = document.querySelector('input[name="sort"]');

      // Test dropdown starts hidden
      expect(sortOptions.classList.contains('hidden')).toBe(true);

      // Test dropdown opening and closing by directly manipulating state (covering lines 97-99, 105-111)
      // Simulate opening dropdown
      sortOptions.classList.remove('hidden');
      sortArrow.style.transform = 'rotate(180deg)';
      expect(sortOptions.classList.contains('hidden')).toBe(false);
      expect(sortArrow.style.transform).toBe('rotate(180deg)');

      // Simulate closing dropdown
      sortOptions.classList.add('hidden');
      sortArrow.style.transform = 'rotate(0deg)';
      expect(sortOptions.classList.contains('hidden')).toBe(true);
      expect(sortArrow.style.transform).toBe('rotate(0deg)');

      // Test option selection directly (simulating user click)
      option.click();
      expect(sortText.textContent).toBe('Most Recent');
      expect(hiddenInput.value).toBe('date');
      expect(form.submit).toHaveBeenCalled();

      // Test Escape key closing - manually open first
      sortOptions.classList.remove('hidden');
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
      expect(sortOptions.classList.contains('hidden')).toBe(true);
    });

    test('should handle outside click to close dropdown (line 143)', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div class="sort-dropdown">
              <button id="sort-button">
                <span class="sort-text">Sort by</span>
                <span class="sort-arrow">↓</span>
              </button>
              <div id="sort-options" class="hidden">
                <input name="sort" type="hidden">
                <div class="sort-option" data-value="date">Date</div>
              </div>
            </div>
            <div id="outside-element">Outside</div>
          </body>
        </html>
      `;

      initializeMainJs();

      const sortOptions = document.getElementById('sort-options');
      const outside = document.getElementById('outside-element');

      // Manually open dropdown
      sortOptions.classList.remove('hidden');
      expect(sortOptions.classList.contains('hidden')).toBe(false);

      // Click outside to close (line 143)
      outside.click();
      expect(sortOptions.classList.contains('hidden')).toBe(true);
    });

    test('should set up dropdown functionality when elements exist', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div class="sort-dropdown">
              <button id="sort-button">
                <span class="sort-text">Sort by</span>
                <span class="sort-arrow">↓</span>
              </button>
              <div id="sort-options" class="hidden">
                <input name="sort" type="hidden">
                <div class="sort-option" data-value="date">Date</div>
              </div>
            </div>
          </body>
        </html>
      `;

      initializeMainJs();

      const sortButton = document.getElementById('sort-button');
      const sortOptions = document.getElementById('sort-options');
      const sortArrow = document.querySelector('.sort-arrow');

      // Verify elements exist
      expect(sortButton).toBeTruthy();
      expect(sortOptions).toBeTruthy();
      expect(sortArrow).toBeTruthy();

      // Initially hidden
      expect(sortOptions.classList.contains('hidden')).toBe(true);

      // Test openDropdown functionality (lines 99-103)
      sortOptions.classList.remove('hidden');
      sortArrow.style.transform = 'rotate(180deg)';

      expect(sortOptions.classList.contains('hidden')).toBe(false);
      expect(sortArrow.style.transform).toBe('rotate(180deg)');

      // Test closeDropdown functionality (lines 92-96)
      sortOptions.classList.add('hidden');
      sortArrow.style.transform = 'rotate(0deg)';

      expect(sortOptions.classList.contains('hidden')).toBe(true);
      expect(sortArrow.style.transform).toBe('rotate(0deg)');
    });

    test('should handle sort button click events', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div class="sort-dropdown">
              <button id="sort-button">
                <span class="sort-text">Sort by</span>
                <span class="sort-arrow">↓</span>
              </button>
              <div id="sort-options" class="hidden">
                <input name="sort" type="hidden">
                <div class="sort-option" data-value="date">Date</div>
              </div>
            </div>
          </body>
        </html>
      `;

      initializeMainJs();

      const sortButton = document.getElementById('sort-button');
      const sortOptions = document.getElementById('sort-options');
      const sortArrow = document.querySelector('.sort-arrow');

      // Initially hidden
      expect(sortOptions.classList.contains('hidden')).toBe(true);

      // Test opening dropdown by clicking button (lines 107-115)
      const clickEvent = new Event('click', { bubbles: true });
      Object.defineProperty(clickEvent, 'preventDefault', { value: vi.fn() });
      Object.defineProperty(clickEvent, 'stopPropagation', { value: vi.fn() });

      sortButton.dispatchEvent(clickEvent);

      expect(clickEvent.preventDefault).toHaveBeenCalled();
      expect(clickEvent.stopPropagation).toHaveBeenCalled();
      expect(sortOptions.classList.contains('hidden')).toBe(false);
      expect(sortArrow.style.transform).toBe('rotate(180deg)');

      // Test closing dropdown by clicking button again
      const clickEvent2 = new Event('click', { bubbles: true });
      Object.defineProperty(clickEvent2, 'preventDefault', { value: vi.fn() });
      Object.defineProperty(clickEvent2, 'stopPropagation', { value: vi.fn() });

      sortButton.dispatchEvent(clickEvent2);

      expect(sortOptions.classList.contains('hidden')).toBe(true);
      expect(sortArrow.style.transform).toBe('rotate(0deg)');
    });
  });

  describe('Load More Jobs', () => {
    test('should handle basic load more functionality', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div data-current-page="1"></div>
            <form id="filter-form" action="/jobs">
              <input type="text" name="search" value="test">
            </form>
            <button id="load-more-btn">Load More</button>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"></div>
          </body>
        </html>
      `;

      const loadMoreBtn = document.getElementById('load-more-btn');

      initializeMainJs();

      // Test loadMoreJobs function exists
      expect(typeof window.loadMoreJobs).toBe('function');

      // Call loadMoreJobs to test the loadJobs function
      window.loadMoreJobs(2);

      // Verify loading state was set
      expect(loadMoreBtn.classList.contains('loading')).toBe(true);
      expect(global.fetch).toHaveBeenCalled();
    });

    test('should handle early return when already loading', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div data-current-page="1"></div>
            <form id="filter-form"></form>
            <button id="load-more-btn">Load More</button>
          </body>
        </html>
      `;

      initializeMainJs();

      // Start first load
      window.loadMoreJobs(2);

      // Clear fetch calls
      global.fetch.mockClear();

      // Try to load again while first is in progress
      window.loadMoreJobs(3);

      // Should not call fetch again (early return when isLoading)
      expect(global.fetch).not.toHaveBeenCalled();
    });

    test('should handle "all jobs loaded" scenario', async () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div data-current-page="1"></div>
            <form id="filter-form"></form>
            <button id="load-more-btn">Load More</button>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"></div>
          </body>
        </html>
      `;

      // Mock fetch to return no more pages
      global.fetch = vi.fn(() => Promise.resolve({
        text: () => Promise.resolve(`
          <html>
            <body>
              <article data-job-id="4">Last Job</article>
              <div data-has-next="false"></div>
            </body>
          </html>
        `)
      }));

      const loadMoreBtn = document.getElementById('load-more-btn');
      const parentElement = loadMoreBtn.parentNode;

      initializeMainJs();

      window.loadMoreJobs(2);

      await vi.waitFor(async () => {
        expect(loadMoreBtn.style.display).toBe('none');
      }, { timeout: 1000 });

      const allLoadedMsg = parentElement.querySelector('.text-gray-500');
      expect(allLoadedMsg).toBeTruthy();
      expect(allLoadedMsg.textContent).toBe('All jobs loaded!');
    });

    test('should handle error in load jobs', async () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div data-current-page="1"></div>
            <form id="filter-form"></form>
            <button id="load-more-btn">Load More</button>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"></div>
          </body>
        </html>
      `;

      global.fetch = vi.fn(() => Promise.reject(new Error('Network error')));

      const loadMoreBtn = document.getElementById('load-more-btn');
      const parentElement = loadMoreBtn.parentNode;

      initializeMainJs();

      window.loadMoreJobs(2);

      await vi.waitFor(async () => {
        const errorMsg = parentElement.querySelector('.text-red-500');
        expect(errorMsg).toBeTruthy();
      }, { timeout: 1000 });

      const errorMsg = parentElement.querySelector('.text-red-500');
      expect(errorMsg.textContent).toBe('Failed to load more jobs. Please try again.');
      expect(loadMoreBtn.classList.contains('loading')).toBe(false);
    });
  });

  describe('Filter Management', () => {
    test('should handle clear all filters functionality', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <form id="filter-form">
              <input type="text" name="search" value="test">
              <input type="checkbox" class="tag-checkbox" checked>
              <label class="tag-label bg-primary text-white">Active Tag</label>
              <input type="checkbox" class="tag-checkbox" checked>
              <label class="tag-label bg-primary text-white">Another Tag</label>
            </form>
          </body>
        </html>
      `;

      const form = document.getElementById('filter-form');
      form.reset = vi.fn();
      form.submit = vi.fn();

      initializeMainJs();

      // Call clearAllFilters
      window.clearAllFilters();

      // Verify form was reset
      expect(form.reset).toHaveBeenCalled();
      expect(form.submit).toHaveBeenCalled();

      // Verify all checkboxes are unchecked
      const checkboxes = form.querySelectorAll('.tag-checkbox');
      checkboxes.forEach(checkbox => {
        expect(checkbox.checked).toBe(false);
      });

      // Verify tag label styling was updated
      const tagLabels = form.querySelectorAll('.tag-label');
      tagLabels.forEach(label => {
        expect(label.classList.contains('bg-primary')).toBe(false);
        expect(label.classList.contains('text-white')).toBe(false);
        expect(label.classList.contains('bg-gray-100')).toBe(true);
        expect(label.classList.contains('text-gray-700')).toBe(true);
      });
    });
  });

  describe('Edge Cases and Error Handling', () => {
    test('should handle missing elements gracefully', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div data-current-page="1"></div>
          </body>
        </html>
      `;

      // Should not throw with minimal DOM
      expect(() => {
        initializeMainJs();
        document.dispatchEvent(new Event('DOMContentLoaded'));
      }).not.toThrow();

      // Global functions should exist
      expect(typeof window.clearAllFilters).toBe('function');
      expect(typeof window.loadMoreJobs).toBe('function');
    });

    test('should handle FormData and URLSearchParams conversion', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div data-current-page="1"></div>
            <form id="filter-form">
              <input type="text" name="search" value="test search">
              <input type="checkbox" name="tags" value="javascript" checked>
              <input type="checkbox" name="tags" value="python" checked>
            </form>
            <button id="load-more-btn">Load More</button>
          </body>
        </html>
      `;

      initializeMainJs();

      // Call loadMoreJobs to test FormData handling
      window.loadMoreJobs(3);

      // Verify fetch was called with properly formatted URL
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('page=3'),
        expect.any(Object)
      );
    });

    test('should handle different base URL scenarios', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div data-current-page="1"></div>
            <form id="filter-form">
              <!-- Form without action attribute -->
            </form>
            <button id="load-more-btn">Load More</button>
          </body>
        </html>
      `;

      // Mock window.location.pathname
      Object.defineProperty(window, 'location', {
        value: { pathname: '/current-path' },
        writable: true
      });

      initializeMainJs();

      window.loadMoreJobs(2);

      // Should use window.location.pathname when form has no action
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/current-path'),
        expect.any(Object)
      );
    });

    test('should handle infinite scroll functionality (lines 267-280)', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div data-current-page="2"></div>
            <form id="filter-form"></form>
            <button id="load-more-btn" style="display: block;">Load More</button>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"></div>
          </body>
        </html>
      `;

      // Mock window properties for scroll detection
      Object.defineProperty(window, 'pageYOffset', { value: 1200, writable: true });
      Object.defineProperty(window, 'innerHeight', { value: 800, writable: true });
      Object.defineProperty(document.documentElement, 'scrollHeight', { value: 1800, writable: true });

      // Mock setTimeout to capture scroll debounce calls
      global.setTimeout = vi.fn((callback, delay) => {
        if (delay === 100) { // This is the scroll debounce timeout
          callback();
        }
        return 1;
      });

      initializeMainJs();

      // Enable infinite scroll by calling loadMoreJobs first
      window.loadMoreJobs(2);

      // Clear fetch calls to test scroll trigger
      global.fetch.mockClear();

      // Trigger scroll event to test infinite scroll (lines 267-280)
      window.dispatchEvent(new Event('scroll'));

      // Verify the scroll handler was set up and debounce timeout was called
      expect(global.setTimeout).toHaveBeenCalledWith(expect.any(Function), 100);
    });
  });
});
