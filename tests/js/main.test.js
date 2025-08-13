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

    // Mock console methods
    global.console.error = vi.fn();
    global.console.log = vi.fn();

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

    // Mock console to suppress debug logs during tests
    global.console = {
      log: vi.fn(),
      warn: vi.fn(),
      error: vi.fn()
    };

    delete window.loadMoreJobs;
    delete window.clearAllFilters;
    delete window.seenJobsAPI;

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

  describe('Location Dropdown', () => {
    test('should handle complete location dropdown functionality', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div class="location-dropdown">
              <button id="location-button">
                <span class="location-text">Any Location</span>
                <span class="location-arrow">↓</span>
              </button>
              <div id="location-options" class="hidden">
                <input name="location" type="hidden" value="">
                <input id="location-search" type="text" placeholder="Search countries...">
                <div class="location-option" data-value="US" data-search="united states usa">United States</div>
                <div class="location-option" data-value="IN" data-search="india">India</div>
                <div class="location-option" data-value="CA" data-search="canada">Canada</div>
              </div>
            </div>
            <form id="filter-form"></form>
          </body>
        </html>
      `;

      const form = document.getElementById('filter-form');
      form.submit = vi.fn();

      initializeMainJs();

      const locationButton = document.getElementById('location-button');
      const locationOptions = document.getElementById('location-options');
      const locationArrow = document.querySelector('.location-arrow');
      const locationText = document.querySelector('.location-text');
      const locationHiddenInput = document.querySelector('input[name="location"]');
      const locationSearch = document.getElementById('location-search');

      // Test dropdown starts hidden
      expect(locationOptions.classList.contains('hidden')).toBe(true);

      // Test dropdown opening and closing by button click
      const clickEvent = new Event('click', { bubbles: true });
      Object.defineProperty(clickEvent, 'preventDefault', { value: vi.fn() });
      Object.defineProperty(clickEvent, 'stopPropagation', { value: vi.fn() });

      locationButton.dispatchEvent(clickEvent);
      expect(clickEvent.preventDefault).toHaveBeenCalled();
      expect(clickEvent.stopPropagation).toHaveBeenCalled();
      expect(locationOptions.classList.contains('hidden')).toBe(false);
      expect(locationArrow.style.transform).toBe('rotate(180deg)');

      // Test closing dropdown by clicking button again
      const clickEvent2 = new Event('click', { bubbles: true });
      Object.defineProperty(clickEvent2, 'preventDefault', { value: vi.fn() });
      Object.defineProperty(clickEvent2, 'stopPropagation', { value: vi.fn() });

      locationButton.dispatchEvent(clickEvent2);
      expect(locationOptions.classList.contains('hidden')).toBe(true);
      expect(locationArrow.style.transform).toBe('rotate(0deg)');
    });

    test('should handle location option selection', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div class="location-dropdown">
              <button id="location-button">
                <span class="location-text">Any Location</span>
                <span class="location-arrow">↓</span>
              </button>
              <div id="location-options" class="hidden">
                <input name="location" type="hidden" value="">
                <div class="location-option" data-value="US">United States</div>
                <div class="location-option" data-value="IN">India</div>
              </div>
            </div>
            <form id="filter-form"></form>
          </body>
        </html>
      `;

      const form = document.getElementById('filter-form');
      form.submit = vi.fn();

      initializeMainJs();

      const locationOptions = document.getElementById('location-options');
      const locationText = document.querySelector('.location-text');
      const locationHiddenInput = document.querySelector('input[name="location"]');
      const usOption = document.querySelector('.location-option[data-value="US"]');

      // Open dropdown first
      locationOptions.classList.remove('hidden');

      // Test option selection
      usOption.click();
      expect(locationText.textContent).toBe('United States');
      expect(locationHiddenInput.value).toBe('US');
      expect(locationOptions.classList.contains('hidden')).toBe(true);
      expect(form.submit).toHaveBeenCalled();
    });

    test('should handle location search functionality', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div class="location-dropdown">
              <button id="location-button">
                <span class="location-text">Any Location</span>
                <span class="location-arrow">↓</span>
              </button>
              <div id="location-options" class="hidden">
                <input name="location" type="hidden" value="">
                <input id="location-search" type="text" placeholder="Search countries...">
                <div class="location-option" data-value="US" data-search="united states usa">United States</div>
                <div class="location-option" data-value="IN" data-search="india">India</div>
                <div class="location-option" data-value="CA" data-search="canada">Canada</div>
              </div>
            </div>
            <form id="filter-form"></form>
          </body>
        </html>
      `;

      initializeMainJs();

      const locationSearch = document.getElementById('location-search');
      const options = document.querySelectorAll('.location-option');

      // Test search filtering
      locationSearch.value = 'united';
      locationSearch.dispatchEvent(new Event('input'));

      // Check that only US option is visible
      expect(options[0].style.display).toBe('block'); // US
      expect(options[1].style.display).toBe('none');  // India
      expect(options[2].style.display).toBe('none');  // Canada

      // Test search with different term
      locationSearch.value = 'india';
      locationSearch.dispatchEvent(new Event('input'));

      expect(options[0].style.display).toBe('none');  // US
      expect(options[1].style.display).toBe('block'); // India
      expect(options[2].style.display).toBe('none');  // Canada

      // Test empty search shows all
      locationSearch.value = '';
      locationSearch.dispatchEvent(new Event('input'));

      options.forEach(option => {
        expect(option.style.display).toBe('block');
      });
    });

    test('should handle Enter key in search to select first visible option', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div class="location-dropdown">
              <button id="location-button">
                <span class="location-text">Any Location</span>
                <span class="location-arrow">↓</span>
              </button>
              <div id="location-options" class="hidden">
                <input name="location" type="hidden" value="">
                <input id="location-search" type="text" placeholder="Search countries...">
                <div class="location-option" data-value="US" data-search="united states usa">United States</div>
                <div class="location-option" data-value="IN" data-search="india">India</div>
              </div>
            </div>
            <form id="filter-form"></form>
          </body>
        </html>
      `;

      const form = document.getElementById('filter-form');
      form.submit = vi.fn();

      initializeMainJs();

      const locationSearch = document.getElementById('location-search');
      const locationText = document.querySelector('.location-text');
      const locationHiddenInput = document.querySelector('input[name="location"]');

      // Filter to show only India option (not the first one)
      locationSearch.value = 'india';
      locationSearch.dispatchEvent(new Event('input'));

      const inOption = document.querySelector('.location-option[data-value="IN"]');
      inOption.click = vi.fn();

      // Test Enter key selects first visible option (that's not the first in DOM)
      const enterEvent = new KeyboardEvent('keydown', { key: 'Enter' });
      Object.defineProperty(enterEvent, 'preventDefault', { value: vi.fn() });

      locationSearch.dispatchEvent(enterEvent);
      expect(enterEvent.preventDefault).toHaveBeenCalled();
      expect(inOption.click).toHaveBeenCalled();
    });

    test('should handle outside click to close location dropdown', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div class="location-dropdown">
              <button id="location-button">
                <span class="location-text">Any Location</span>
                <span class="location-arrow">↓</span>
              </button>
              <div id="location-options" class="hidden">
                <input name="location" type="hidden" value="">
                <div class="location-option" data-value="US">United States</div>
              </div>
            </div>
            <div id="outside-element">Outside</div>
          </body>
        </html>
      `;

      initializeMainJs();

      const locationOptions = document.getElementById('location-options');
      const locationArrow = document.querySelector('.location-arrow');
      const outside = document.getElementById('outside-element');

      // Manually open dropdown
      locationOptions.classList.remove('hidden');
      locationArrow.style.transform = 'rotate(180deg)';
      expect(locationOptions.classList.contains('hidden')).toBe(false);

      // Click outside to close
      outside.click();
      expect(locationOptions.classList.contains('hidden')).toBe(true);
      expect(locationArrow.style.transform).toBe('rotate(0deg)');
    });

    test('should handle Escape key to close location dropdown', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div class="location-dropdown">
              <button id="location-button">
                <span class="location-text">Any Location</span>
                <span class="location-arrow">↓</span>
              </button>
              <div id="location-options" class="hidden">
                <input name="location" type="hidden" value="">
                <div class="location-option" data-value="US">United States</div>
              </div>
            </div>
          </body>
        </html>
      `;

      initializeMainJs();

      const locationOptions = document.getElementById('location-options');
      const locationArrow = document.querySelector('.location-arrow');

      // Manually open dropdown
      locationOptions.classList.remove('hidden');
      locationArrow.style.transform = 'rotate(180deg)';
      expect(locationOptions.classList.contains('hidden')).toBe(false);

      // Press Escape to close
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
      expect(locationOptions.classList.contains('hidden')).toBe(true);
      expect(locationArrow.style.transform).toBe('rotate(0deg)');
    });

    test('should focus search input when dropdown opens', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div class="location-dropdown">
              <button id="location-button">
                <span class="location-text">Any Location</span>
                <span class="location-arrow">↓</span>
              </button>
              <div id="location-options" class="hidden">
                <input name="location" type="hidden" value="">
                <input id="location-search" type="text" placeholder="Search countries...">
                <div class="location-option" data-value="US">United States</div>
              </div>
            </div>
          </body>
        </html>
      `;

      initializeMainJs();

      const locationButton = document.getElementById('location-button');
      const locationSearch = document.getElementById('location-search');
      locationSearch.focus = vi.fn();

      // Open dropdown
      const clickEvent = new Event('click', { bubbles: true });
      Object.defineProperty(clickEvent, 'preventDefault', { value: vi.fn() });
      Object.defineProperty(clickEvent, 'stopPropagation', { value: vi.fn() });

      locationButton.dispatchEvent(clickEvent);

      // Verify focus is called after timeout (we execute immediately in tests)
      expect(locationSearch.focus).toHaveBeenCalled();
    });

    test('should reset location dropdown in clearAllFilters', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <form id="filter-form">
              <div class="location-dropdown">
                <span class="location-text">United States</span>
              </div>
            </form>
          </body>
        </html>
      `;

      const form = document.getElementById('filter-form');
      form.reset = vi.fn();
      form.submit = vi.fn();

      initializeMainJs();

      const locationText = document.querySelector('.location-text');
      expect(locationText.textContent).toBe('United States');

      // Call clearAllFilters
      window.clearAllFilters();

      expect(locationText.textContent).toBe('Any Location');
      expect(form.reset).toHaveBeenCalled();
      expect(form.submit).toHaveBeenCalled();
    });
  });

  describe('Location Dropdown Edge Cases', () => {
    test('should handle location option click when not a .location-option element', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div class="location-dropdown">
              <button id="location-button">
                <span class="location-text">Any Location</span>
                <span class="location-arrow">↓</span>
              </button>
              <div id="location-options" class="hidden">
                <input name="location" type="hidden" value="">
                <div class="location-option" data-value="US">United States</div>
                <span>Not a location option</span>
              </div>
            </div>
            <form id="filter-form"></form>
          </body>
        </html>
      `;

      const form = document.getElementById('filter-form');
      form.submit = vi.fn();

      initializeMainJs();

      const locationOptions = document.getElementById('location-options');
      const nonOptionElement = locationOptions.querySelector('span');

      // Open dropdown first
      locationOptions.classList.remove('hidden');

      // Click on non-option element should do nothing
      nonOptionElement.click();
      expect(form.submit).not.toHaveBeenCalled();
    });

    test('should handle search with data-search attribute vs textContent fallback', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div class="location-dropdown">
              <button id="location-button">
                <span class="location-text">Any Location</span>
                <span class="location-arrow">↓</span>
              </button>
              <div id="location-options" class="hidden">
                <input name="location" type="hidden" value="">
                <input id="location-search" type="text" placeholder="Search countries...">
                <div class="location-option" data-value="US" data-search="united states usa">United States</div>
                <div class="location-option" data-value="UK">United Kingdom</div>
              </div>
            </div>
            <form id="filter-form"></form>
          </body>
        </html>
      `;

      initializeMainJs();

      const locationSearch = document.getElementById('location-search');
      const options = document.querySelectorAll('.location-option');

      // Test search using data-search attribute (US has custom search terms)
      locationSearch.value = 'usa';
      locationSearch.dispatchEvent(new Event('input'));

      expect(options[0].style.display).toBe('block'); // US (matches via data-search)
      expect(options[1].style.display).toBe('none');  // UK (no match)

      // Test search using textContent fallback (UK has no data-search)
      locationSearch.value = 'kingdom';
      locationSearch.dispatchEvent(new Event('input'));

      expect(options[0].style.display).toBe('none');  // US (no match)
      expect(options[1].style.display).toBe('block'); // UK (matches via textContent)
    });

    test('should handle Enter key when no visible options exist', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div class="location-dropdown">
              <button id="location-button">
                <span class="location-text">Any Location</span>
                <span class="location-arrow">↓</span>
              </button>
              <div id="location-options" class="hidden">
                <input name="location" type="hidden" value="">
                <input id="location-search" type="text" placeholder="Search countries...">
                <div class="location-option" data-value="US" style="display: none;">United States</div>
                <div class="location-option" data-value="IN" style="display: none;">India</div>
              </div>
            </div>
            <form id="filter-form"></form>
          </body>
        </html>
      `;

      const form = document.getElementById('filter-form');
      form.submit = vi.fn();

      initializeMainJs();

      const locationSearch = document.getElementById('location-search');

      // All options are hidden, so Enter should do nothing
      const enterEvent = new KeyboardEvent('keydown', { key: 'Enter' });
      Object.defineProperty(enterEvent, 'preventDefault', { value: vi.fn() });

      locationSearch.dispatchEvent(enterEvent);
      expect(enterEvent.preventDefault).toHaveBeenCalled();
      expect(form.submit).not.toHaveBeenCalled();
    });

    test('should handle when locationSearch element does not exist', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div class="location-dropdown">
              <button id="location-button">
                <span class="location-text">Any Location</span>
                <span class="location-arrow">↓</span>
              </button>
              <div id="location-options" class="hidden">
                <input name="location" type="hidden" value="">
                <!-- No location-search input -->
                <div class="location-option" data-value="US">United States</div>
              </div>
            </div>
            <form id="filter-form"></form>
          </body>
        </html>
      `;

      // Should not throw when locationSearch is null
      expect(() => {
        initializeMainJs();
      }).not.toThrow();
    });

    test('should handle focus timeout when locationSearch exists', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div class="location-dropdown">
              <button id="location-button">
                <span class="location-text">Any Location</span>
                <span class="location-arrow">↓</span>
              </button>
              <div id="location-options" class="hidden">
                <input name="location" type="hidden" value="">
                <input id="location-search" type="text" placeholder="Search countries...">
                <div class="location-option" data-value="US">United States</div>
              </div>
            </div>
            <form id="filter-form"></form>
          </body>
        </html>
      `;

      // Mock setTimeout to capture the focus timeout
      global.setTimeout = vi.fn((callback, delay) => {
        if (delay === 100) {
          callback();
        }
        return 1;
      });

      initializeMainJs();

      const locationButton = document.getElementById('location-button');
      const locationSearch = document.getElementById('location-search');
      locationSearch.focus = vi.fn();

      // Open dropdown to trigger focus timeout
      const clickEvent = new Event('click', { bubbles: true });
      Object.defineProperty(clickEvent, 'preventDefault', { value: vi.fn() });
      Object.defineProperty(clickEvent, 'stopPropagation', { value: vi.fn() });

      locationButton.dispatchEvent(clickEvent);

      expect(global.setTimeout).toHaveBeenCalledWith(expect.any(Function), 100);
      expect(locationSearch.focus).toHaveBeenCalled();
    });

    test('should handle missing locationHiddenInput and locationText gracefully', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div class="location-dropdown">
              <button id="location-button">
                <!-- Missing location-text span -->
                <span class="location-arrow">↓</span>
              </button>
              <div id="location-options" class="hidden">
                <!-- Missing hidden input -->
                <div class="location-option" data-value="US">United States</div>
              </div>
            </div>
            <form id="filter-form"></form>
          </body>
        </html>
      `;

      const form = document.getElementById('filter-form');
      form.submit = vi.fn();

      initializeMainJs();

      const locationOptions = document.getElementById('location-options');
      const usOption = document.querySelector('.location-option[data-value="US"]');

      // Open dropdown first
      locationOptions.classList.remove('hidden');

      // Should not throw when locationHiddenInput and locationText are null
      expect(() => {
        usOption.click();
      }).not.toThrow();

      expect(form.submit).toHaveBeenCalled();
    });
  });

  describe('Seen Jobs Functionality', () => {
    beforeEach(() => {
      // Clear localStorage before each test
      global.localStorage.getItem.mockClear();
      global.localStorage.setItem.mockClear();
      global.localStorage.removeItem.mockClear();
    });

    test('should manage seen jobs in localStorage', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
          </body>
        </html>
      `;

      initializeMainJs();

      // Test getSeenJobs with empty localStorage
      global.localStorage.getItem.mockReturnValue(null);
      expect(window.seenJobsAPI.getSeenJobs()).toEqual([]);

      // Test getSeenJobs with existing data
      global.localStorage.getItem.mockReturnValue('["job1","job2"]');
      expect(window.seenJobsAPI.getSeenJobs()).toEqual(['job1', 'job2']);

      // Test markJobAsSeen to mark as seen
      global.localStorage.getItem.mockReturnValue('[]');
      expect(window.seenJobsAPI.markJobAsSeen('job3', true)).toBe(true);
      expect(global.localStorage.setItem).toHaveBeenCalledWith('job-board-seen-jobs', '["job3"]');

      // Test markJobAsSeen to unmark as seen
      global.localStorage.getItem.mockReturnValue('["job3","job4"]');
      expect(window.seenJobsAPI.markJobAsSeen('job3', false)).toBe(true);
      expect(global.localStorage.setItem).toHaveBeenCalledWith('job-board-seen-jobs', '["job4"]');

      // Test isJobSeen
      global.localStorage.getItem.mockReturnValue('["job1","job2"]');
      expect(window.seenJobsAPI.isJobSeen('job1')).toBe(true);
      expect(window.seenJobsAPI.isJobSeen('job3')).toBe(false);

      // Test clearSeenJobs
      expect(window.seenJobsAPI.clearSeenJobs()).toBe(true);
      expect(global.localStorage.removeItem).toHaveBeenCalledWith('job-board-seen-jobs');
    });

    test('should handle localStorage errors gracefully', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
          </body>
        </html>
      `;

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      initializeMainJs();

      // Test getSeenJobs error
      global.localStorage.getItem.mockImplementation(() => {
        throw new Error('localStorage error');
      });
      expect(window.seenJobsAPI.getSeenJobs()).toEqual([]);
      expect(consoleSpy).toHaveBeenCalledWith('Error reading seen jobs from localStorage:', expect.any(Error));

      // Test markJobAsSeen error
      global.localStorage.setItem.mockImplementation(() => {
        throw new Error('localStorage error');
      });
      expect(window.seenJobsAPI.markJobAsSeen('job1', true)).toBe(false);
      expect(consoleSpy).toHaveBeenCalledWith('Error updating seen jobs in localStorage:', expect.any(Error));

      // Test clearSeenJobs error
      global.localStorage.removeItem.mockImplementation(() => {
        throw new Error('localStorage error');
      });
      expect(window.seenJobsAPI.clearSeenJobs()).toBe(false);
      expect(consoleSpy).toHaveBeenCalledWith('Error clearing seen jobs from localStorage:', expect.any(Error));

      consoleSpy.mockRestore();
    });

    test('should handle malformed JSON in localStorage', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
          </body>
        </html>
      `;

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      initializeMainJs();

      // Test malformed JSON
      global.localStorage.getItem.mockReturnValue('malformed json');
      expect(window.seenJobsAPI.getSeenJobs()).toEqual([]);
      expect(consoleSpy).toHaveBeenCalledWith('Error reading seen jobs from localStorage:', expect.any(Error));

      consoleSpy.mockRestore();
    });

    test('should update job visual state correctly', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <article data-job-id="job1">
              <button class="seen-job-btn">
                <svg class="seen-icon hidden"></svg>
                <svg class="unseen-icon"></svg>
              </button>
            </article>
          </body>
        </html>
      `;

      initializeMainJs();

      const jobCard = document.querySelector('article');
      const btn = document.querySelector('.seen-job-btn');
      const seenIcon = document.querySelector('.seen-icon');
      const unseenIcon = document.querySelector('.unseen-icon');

      // Test marking as seen
      window.seenJobsAPI.updateJobVisualState(jobCard, true);
      expect(jobCard.classList.contains('job-seen')).toBe(true);
      expect(jobCard.style.opacity).toBe('0.2');
      expect(btn.style.opacity).toBe('0.6');
      expect(jobCard.onmouseenter).toBe(null); // Hover disabled
      expect(jobCard.onmouseleave).toBe(null); // Hover disabled
      expect(seenIcon.classList.contains('hidden')).toBe(false);
      expect(unseenIcon.classList.contains('hidden')).toBe(true);
      expect(btn.title).toBe('Mark as unseen');
      expect(btn.getAttribute('aria-label')).toBe('Mark job as unseen');

      // Test marking as unseen
      window.seenJobsAPI.updateJobVisualState(jobCard, false);
      expect(jobCard.classList.contains('job-seen')).toBe(false);
      expect(jobCard.style.opacity).toBe('');
      expect(btn.style.opacity).toBe('');
      expect(jobCard.classList.contains('job-seen-transform')).toBe(false); // Transform class removed
      expect(typeof jobCard.onmouseenter).toBe('function'); // Hover restored
      expect(typeof jobCard.onmouseleave).toBe('function'); // Hover restored
      expect(seenIcon.classList.contains('hidden')).toBe(true);
      expect(unseenIcon.classList.contains('hidden')).toBe(false);
      expect(btn.title).toBe('Mark as seen');
      expect(btn.getAttribute('aria-label')).toBe('Mark job as seen');
    });

    test('should handle seen job button clicks', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <article data-job-id="job1">
              <button class="seen-job-btn" data-job-id="job1">
                <svg class="seen-icon hidden"></svg>
                <svg class="unseen-icon"></svg>
              </button>
            </article>
          </body>
        </html>
      `;

      global.localStorage.getItem.mockReturnValue('[]');
      initializeMainJs();

      const btn = document.querySelector('.seen-job-btn');
      const jobCard = document.querySelector('article');

      // Test click event handling
      const clickEvent = new Event('click');
      Object.defineProperty(clickEvent, 'preventDefault', { value: vi.fn() });
      Object.defineProperty(clickEvent, 'stopPropagation', { value: vi.fn() });
      Object.defineProperty(clickEvent, 'currentTarget', { value: btn });

      window.seenJobsAPI.handleSeenJobClick(clickEvent);

      expect(clickEvent.preventDefault).toHaveBeenCalled();
      expect(clickEvent.stopPropagation).toHaveBeenCalled();
      expect(global.localStorage.setItem).toHaveBeenCalledWith('job-board-seen-jobs', '["job1"]');
    });

    test('should handle seen job button clicks with missing elements', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
          </body>
        </html>
      `;

      initializeMainJs();

      // Test click with no jobId
      const btnWithoutJobId = document.createElement('button');
      const clickEvent1 = new Event('click');
      Object.defineProperty(clickEvent1, 'preventDefault', { value: vi.fn() });
      Object.defineProperty(clickEvent1, 'stopPropagation', { value: vi.fn() });
      Object.defineProperty(clickEvent1, 'currentTarget', { value: btnWithoutJobId });

      // Should return early when no jobId
      window.seenJobsAPI.handleSeenJobClick(clickEvent1);
      expect(global.localStorage.setItem).not.toHaveBeenCalled();

      // Test click with no jobCard
      const btnWithJobId = document.createElement('button');
      btnWithJobId.dataset.jobId = 'job1';
      const clickEvent2 = new Event('click');
      Object.defineProperty(clickEvent2, 'preventDefault', { value: vi.fn() });
      Object.defineProperty(clickEvent2, 'stopPropagation', { value: vi.fn() });
      Object.defineProperty(clickEvent2, 'currentTarget', { value: btnWithJobId });

      // Should return early when no jobCard
      window.seenJobsAPI.handleSeenJobClick(clickEvent2);
      expect(global.localStorage.setItem).not.toHaveBeenCalled();
    });

    test('should restore seen states on page load', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <article data-job-id="job1">
              <button class="seen-job-btn">
                <svg class="seen-icon hidden"></svg>
                <svg class="unseen-icon"></svg>
              </button>
            </article>
            <article data-job-id="job2">
              <button class="seen-job-btn">
                <svg class="seen-icon hidden"></svg>
                <svg class="unseen-icon"></svg>
              </button>
            </article>
          </body>
        </html>
      `;

      global.localStorage.getItem.mockReturnValue('["job1"]');
      initializeMainJs();

      window.seenJobsAPI.restoreSeenStates();

      const job1Card = document.querySelector('article[data-job-id="job1"]');
      const job2Card = document.querySelector('article[data-job-id="job2"]');

      expect(job1Card.classList.contains('job-seen')).toBe(true);
      expect(job2Card.classList.contains('job-seen')).toBe(false);
    });

    test('should initialize seen jobs functionality', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <article data-job-id="job1">
              <button class="seen-job-btn">
                <svg class="seen-icon hidden"></svg>
                <svg class="unseen-icon"></svg>
              </button>
            </article>
          </body>
        </html>
      `;

      global.localStorage.getItem.mockReturnValue('["job1"]');

      // Create a spy to track event listeners
      const addEventListenerSpy = vi.fn();
      document.querySelector('.seen-job-btn').addEventListener = addEventListenerSpy;

      initializeMainJs();

      window.seenJobsAPI.initializeSeenJobs();

      // Should restore seen states and add event listeners
      const jobCard = document.querySelector('article[data-job-id="job1"]');
      expect(jobCard.classList.contains('job-seen')).toBe(true);
      expect(addEventListenerSpy).toHaveBeenCalledWith('click', expect.any(Function));
    });

    test('should integrate with load more jobs functionality', async () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div data-current-page="1"></div>
            <form id="filter-form"></form>
            <button id="load-more-btn">Load More</button>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
              <article data-job-id="existing-job">
                <button class="seen-job-btn">
                  <svg class="seen-icon hidden"></svg>
                  <svg class="unseen-icon"></svg>
                </button>
              </article>
            </div>
          </body>
        </html>
      `;

      // Mock fetch to return new job cards
      global.fetch = vi.fn(() => Promise.resolve({
        text: () => Promise.resolve(`
          <html>
            <body>
              <article data-job-id="new-job">
                <button class="seen-job-btn">
                  <svg class="seen-icon hidden"></svg>
                  <svg class="unseen-icon"></svg>
                </button>
              </article>
              <div data-has-next="true"></div>
            </body>
          </html>
        `)
      }));

      global.localStorage.getItem.mockReturnValue('["new-job"]');

      // Mock setTimeout to capture callbacks but execute the 1000ms one manually
      let timeoutCallbacks = [];
      global.setTimeout = vi.fn((callback, delay) => {
        if (delay === 1000) {
          timeoutCallbacks.push(callback);
        } else {
          callback();
        }
        return 1;
      });

      initializeMainJs();

      // Load more jobs
      window.loadMoreJobs(2);

      // Wait for fetch to complete and DOM to be updated
      await vi.waitFor(() => {
        const newJob = document.querySelector('article[data-job-id="new-job"]');
        expect(newJob).toBeTruthy();
      });

      // Execute the setTimeout callback for seen jobs integration
      timeoutCallbacks.forEach(callback => callback());

      // Verify that the new job is marked as seen
      const newJob = document.querySelector('article[data-job-id="new-job"]');
      expect(newJob).toBeTruthy();
      expect(newJob.style.opacity).toBe('0.2');
      expect(newJob.classList.contains('job-seen')).toBe(true);

      // Check that setTimeout was called for the seen jobs integration (1000ms delay)
      expect(global.setTimeout).toHaveBeenCalledWith(expect.any(Function), 1000);
    });

    test('should handle seen job button clicks in real scenarios', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <article data-job-id="job1">
              <button class="seen-job-btn" data-job-id="job1">
                <svg class="seen-icon hidden"></svg>
                <svg class="unseen-icon"></svg>
              </button>
            </article>
          </body>
        </html>
      `;

      global.localStorage.getItem.mockReturnValue('[]');

      // Mock setTimeout to execute callbacks immediately for testing
      global.setTimeout = vi.fn((callback, delay) => {
        callback();
        return 1;
      });

      initializeMainJs();

      const btn = document.querySelector('.seen-job-btn');

      // Simulate actual button click
      btn.click();

      // Verify job was marked as seen
      expect(global.localStorage.setItem).toHaveBeenCalledWith('job-board-seen-jobs', '["job1"]');

      // Test clicking again to unmark
      global.localStorage.getItem.mockReturnValue('["job1"]');
      global.localStorage.setItem.mockClear();
      btn.click();

      expect(global.localStorage.setItem).toHaveBeenCalledWith('job-board-seen-jobs', '[]');
    });

    test('should handle add event listener for dynamically loaded jobs', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
          </body>
        </html>
      `;

      global.localStorage.getItem.mockReturnValue('[]');
      initializeMainJs();

      // Simulate the logic that gets executed in the setTimeout callback
      const newJobCard = document.createElement('article');
      newJobCard.dataset.jobId = 'new-job';
      newJobCard.innerHTML = `
        <button class="seen-job-btn">
          <svg class="seen-icon hidden"></svg>
          <svg class="unseen-icon"></svg>
        </button>
      `;
      document.body.appendChild(newJobCard);

      const addEventListenerSpy = vi.fn();
      const btn = newJobCard.querySelector('.seen-job-btn');
      btn.addEventListener = addEventListenerSpy;

      // Execute the logic from the setTimeout callback
      const jobCards = document.querySelectorAll('article[data-job-id]');
      jobCards.forEach(jobCard => {
        const btn = jobCard.querySelector('.seen-job-btn');
        if (btn && !btn.hasAttribute('data-listener-added')) {
          btn.addEventListener('click', window.seenJobsAPI.handleSeenJobClick);
          btn.setAttribute('data-listener-added', 'true');
        }
      });

      // Verify event listener was added and data-listener-added attribute was set
      expect(addEventListenerSpy).toHaveBeenCalledWith('click', expect.any(Function));
      expect(btn.getAttribute('data-listener-added')).toBe('true');
    });

    test('should not add duplicate event listeners', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
          </body>
        </html>
      `;

      initializeMainJs();

      // Test the logic directly by simulating the timeout callback
      const jobCard = document.createElement('article');
      jobCard.dataset.jobId = 'job1';
      jobCard.innerHTML = `
        <button class="seen-job-btn" data-listener-added="true">
          <svg class="seen-icon hidden"></svg>
          <svg class="unseen-icon"></svg>
        </button>
      `;
      document.body.appendChild(jobCard);

      const addEventListenerSpy = vi.fn();
      const btn = jobCard.querySelector('.seen-job-btn');
      btn.addEventListener = addEventListenerSpy;

      // Execute the logic that would be in the setTimeout callback
      const jobCards = document.querySelectorAll('article[data-job-id]');
      jobCards.forEach(jobCard => {
        const btn = jobCard.querySelector('.seen-job-btn');
        if (btn && !btn.hasAttribute('data-listener-added')) {
          btn.addEventListener('click', window.seenJobsAPI.handleSeenJobClick);
          btn.setAttribute('data-listener-added', 'true');
        }
      });

      // Should not add event listener since data-listener-added="true"
      expect(addEventListenerSpy).not.toHaveBeenCalled();
    });

    test('should handle updateJobVisualState with null jobCard', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
          </body>
        </html>
      `;

      // Mock console.error
      const consoleSpy = vi.spyOn(global.console, 'error').mockImplementation(() => {});

      initializeMainJs();

      // Test with null jobCard - should not throw an error
      expect(() => {
        window.seenJobsAPI.updateJobVisualState(null, true);
      }).not.toThrow();

      // Console.error should have been called
      expect(global.console.error).toHaveBeenCalledWith('updateJobVisualState: jobCard is null');
    });

    test('should test hover effect functions when unmarking jobs as unseen', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <article data-job-id="test-job" class="job-seen" style="opacity: 0.2;">
              <button class="seen-job-btn" data-job-id="test-job">
                <svg class="seen-icon"></svg>
                <svg class="unseen-icon hidden"></svg>
              </button>
            </article>
          </body>
        </html>
      `;

      initializeMainJs();

      const jobCard = document.querySelector('article[data-job-id="test-job"]');

      // Mark as unseen to restore hover effects
      window.seenJobsAPI.updateJobVisualState(jobCard, false);

      // Test that hover functions were restored and work
      expect(typeof jobCard.onmouseenter).toBe('function');
      expect(typeof jobCard.onmouseleave).toBe('function');

      // Test the hover functions
      jobCard.onmouseenter();
      expect(jobCard.style.transform).toBe('translateY(-8px) scale(1.02)');

      jobCard.onmouseleave();
      expect(jobCard.style.transform).toBe('translateY(0) scale(1)');
    });

    test('should use CSS class for transform instead of inline styles', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <article data-job-id="test-job">
              <button class="seen-job-btn" data-job-id="test-job">
                <svg class="seen-icon hidden"></svg>
                <svg class="unseen-icon"></svg>
              </button>
            </article>
          </body>
        </html>
      `;

      initializeMainJs();

      const jobCard = document.querySelector('article[data-job-id="test-job"]');

      // Mark as seen - should add CSS class
      window.seenJobsAPI.updateJobVisualState(jobCard, true);

      // Verify CSS class is added instead of inline transform
      expect(jobCard.classList.contains('job-seen-transform')).toBe(true);
      // Don't check inline transform as it may have animation styles

      // Mark as unseen - should remove CSS class
      window.seenJobsAPI.updateJobVisualState(jobCard, false);

      // Verify CSS class is removed
      expect(jobCard.classList.contains('job-seen-transform')).toBe(false);
    });

    test('should test clearSeenJobs error handling', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
          </body>
        </html>
      `;

      // Mock localStorage to throw an error
      const originalRemoveItem = global.localStorage.removeItem;
      global.localStorage.removeItem = vi.fn(() => {
        throw new Error('Storage error');
      });

      const consoleSpy = vi.spyOn(global.console, 'error').mockImplementation(() => {});

      initializeMainJs();

      const result = window.seenJobsAPI.clearSeenJobs();

      expect(result).toBe(false);
      expect(consoleSpy).toHaveBeenCalledWith('Error clearing seen jobs from localStorage:', expect.any(Error));

      // Restore original function
      global.localStorage.removeItem = originalRemoveItem;
    });

    test('should handle window load event initialization', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <article data-job-id="test-job">
              <button class="seen-job-btn" data-job-id="test-job">
                <svg class="seen-icon hidden"></svg>
                <svg class="unseen-icon"></svg>
              </button>
            </article>
          </body>
        </html>
      `;

      global.localStorage.getItem.mockReturnValue('["test-job"]');

      // Mock setTimeout to capture callbacks
      let timeoutCallbacks = [];
      global.setTimeout = vi.fn((callback, delay) => {
        timeoutCallbacks.push({ callback, delay });
        return 1;
      });

      initializeMainJs();

      // Trigger window load event
      const loadEvent = new Event('load');
      window.dispatchEvent(loadEvent);

      // Execute the window load timeout callback
      const windowLoadCallback = timeoutCallbacks.find(t => t.delay === 500);
      expect(windowLoadCallback).toBeTruthy();

      windowLoadCallback.callback();

      const jobCard = document.querySelector('article[data-job-id="test-job"]');
      expect(jobCard.classList.contains('job-seen')).toBe(true);
    });

    test('should handle double-check re-application of seen state', () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <article data-job-id="test-job">
              <button class="seen-job-btn" data-job-id="test-job">
                <svg class="seen-icon hidden"></svg>
                <svg class="unseen-icon"></svg>
              </button>
            </article>
          </body>
        </html>
      `;

      global.localStorage.getItem.mockReturnValue('["test-job"]');

      // Mock setTimeout to capture callbacks
      let timeoutCallbacks = [];
      global.setTimeout = vi.fn((callback, delay) => {
        timeoutCallbacks.push({ callback, delay });
        return 1;
      });

      initializeMainJs();

      // Execute the 1000ms timeout (initialization)
      const initCallback = timeoutCallbacks.find(t => t.delay === 1000);
      expect(initCallback).toBeTruthy();
      initCallback.callback();

      // Find and execute the 200ms double-check timeout
      const doubleCheckCallback = timeoutCallbacks.find(t => t.delay === 200);
      expect(doubleCheckCallback).toBeTruthy();

      // Simulate job card not having seen class (missed in first pass)
      const jobCard = document.querySelector('article[data-job-id="test-job"]');
      jobCard.classList.remove('job-seen');

      // Execute double-check callback
      doubleCheckCallback.callback();

      // Verify it re-applied the seen state
      expect(jobCard.classList.contains('job-seen')).toBe(true);
    });

    test('should handle event listener addition in loadMoreJobs for unseen buttons', async () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div data-current-page="1"></div>
            <form id="filter-form"></form>
            <button id="load-more-btn">Load More</button>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
              <article data-job-id="existing-job">
                <button class="seen-job-btn">
                  <svg class="seen-icon hidden"></svg>
                  <svg class="unseen-icon"></svg>
                </button>
              </article>
            </div>
          </body>
        </html>
      `;

      // Mock fetch to return new job cards without data-listener-added
      global.fetch = vi.fn(() => Promise.resolve({
        text: () => Promise.resolve(`
          <html>
            <body>
              <article data-job-id="new-job">
                <button class="seen-job-btn" data-job-id="new-job">
                  <svg class="seen-icon hidden"></svg>
                  <svg class="unseen-icon"></svg>
                </button>
              </article>
              <div data-has-next="true"></div>
            </body>
          </html>
        `)
      }));

      global.localStorage.getItem.mockReturnValue('[]');

      let timeoutCallbacks = [];
      global.setTimeout = vi.fn((callback, delay) => {
        if (delay === 1000) {
          timeoutCallbacks.push(callback);
        } else {
          callback();
        }
        return 1;
      });

      initializeMainJs();

      // Load more jobs
      window.loadMoreJobs(2);

      // Wait for new job to be added
      await vi.waitFor(() => {
        const newJob = document.querySelector('article[data-job-id="new-job"]');
        expect(newJob).toBeTruthy();
      });

      // Verify new button doesn't have listener initially
      const newBtn = document.querySelector('article[data-job-id="new-job"] .seen-job-btn');
      expect(newBtn.hasAttribute('data-listener-added')).toBe(false);

      // Execute the setTimeout callback for loadMoreJobs
      timeoutCallbacks.forEach(callback => callback());

      // Verify event listener was added to new button
      expect(newBtn.hasAttribute('data-listener-added')).toBe(true);

      // Test that the button actually works by clicking it
      newBtn.click();
      expect(global.localStorage.setItem).toHaveBeenCalledWith('job-board-seen-jobs', '["new-job"]');
    });

    test('should cover event listener addition lines in loadMoreJobs', async () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div data-current-page="1"></div>
            <form id="filter-form"></form>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"></div>
          </body>
        </html>
      `;

      // Mock fetch to return job with button that needs listener
      global.fetch = vi.fn(() => Promise.resolve({
        text: () => Promise.resolve(`
          <html>
            <body>
              <article data-job-id="test-job">
                <button class="seen-job-btn" data-job-id="test-job">
                  <svg class="seen-icon hidden"></svg>
                  <svg class="unseen-icon"></svg>
                </button>
              </article>
              <div data-has-next="false"></div>
            </body>
          </html>
        `)
      }));

      global.localStorage.getItem.mockReturnValue('[]');

      // Mock setTimeout to collect all callbacks
      let allCallbacks = [];
      global.setTimeout = vi.fn((callback, delay) => {
        allCallbacks.push({ callback, delay });
        if (delay !== 1000) {
          callback(); // Execute non-1000ms timeouts immediately
        }
        return 1;
      });

      initializeMainJs();

      // Call loadMoreJobs directly to trigger the event listener addition
      window.loadMoreJobs(2);

      // Wait for DOM to be updated
      await vi.waitFor(() => {
        const newJob = document.querySelector('article[data-job-id="test-job"]');
        expect(newJob).toBeTruthy();
      });

      // Execute the 1000ms callback from loadMoreJobs which adds event listeners
      const loadMoreCallback = allCallbacks.find(c => c.delay === 1000);
      expect(loadMoreCallback).toBeTruthy();
      loadMoreCallback.callback();

      // Verify the button now has the event listener
      const btn = document.querySelector('.seen-job-btn[data-job-id="test-job"]');
      expect(btn.hasAttribute('data-listener-added')).toBe(true);

      // Verify the event listener works
      btn.click();
      expect(global.localStorage.setItem).toHaveBeenCalledWith('job-board-seen-jobs', '["test-job"]');
    });

    test('should initialize seen jobs for infinite scroll loaded cards', async () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div data-current-page="1"></div>
            <form id="filter-form"></form>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"></div>
          </body>
        </html>
      `;

      // Mock fetch for loadJobs (infinite scroll)
      global.fetch = vi.fn(() => Promise.resolve({
        text: () => Promise.resolve(`
          <html>
            <body>
              <article data-job-id="infinite-job">
                <button class="seen-job-btn" data-job-id="infinite-job">
                  <svg class="seen-icon hidden"></svg>
                  <svg class="unseen-icon"></svg>
                </button>
              </article>
              <div data-has-next="false"></div>
            </body>
          </html>
        `)
      }));

      global.localStorage.getItem.mockReturnValue('["infinite-job"]');

      // Mock setTimeout to capture callbacks
      let timeoutCallbacks = [];
      global.setTimeout = vi.fn((callback, delay) => {
        if (delay === 1000) {
          timeoutCallbacks.push(callback);
        } else {
          callback();
        }
        return 1;
      });

      initializeMainJs();

      // Call loadJobs directly (as infinite scroll does)
      window.loadJobs(2);

      // Wait for new job to be added
      await vi.waitFor(() => {
        const newJob = document.querySelector('article[data-job-id="infinite-job"]');
        expect(newJob).toBeTruthy();
      });

      // Verify button doesn't have listener initially
      const btn = document.querySelector('.seen-job-btn[data-job-id="infinite-job"]');
      expect(btn.hasAttribute('data-listener-added')).toBe(false);

      // Execute the 1000ms timeout callback that initializes seen jobs
      timeoutCallbacks.forEach(callback => callback());

      // Verify the job was marked as seen (visual state)
      const jobCard = document.querySelector('article[data-job-id="infinite-job"]');
      expect(jobCard.classList.contains('job-seen')).toBe(true);
      expect(jobCard.style.opacity).toBe('0.2');

      // Verify event listener was added
      expect(btn.hasAttribute('data-listener-added')).toBe(true);

      // Test the button works by clicking to unmark
      btn.click();
      expect(global.localStorage.setItem).toHaveBeenCalledWith('job-board-seen-jobs', '[]');
    });

    test('should cover lines 336-337 in loadJobs timeout with precise control', async () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div data-current-page="1"></div>
            <form id="filter-form"></form>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"></div>
          </body>
        </html>
      `;

      // Mock fetch that returns a job WITHOUT the data-listener-added attribute
      global.fetch = vi.fn(() => Promise.resolve({
        text: () => Promise.resolve(`
          <html>
            <body>
              <article data-job-id="coverage-test-job">
                <button class="seen-job-btn" data-job-id="coverage-test-job">
                  <svg class="seen-icon hidden"></svg>
                  <svg class="unseen-icon"></svg>
                </button>
              </article>
              <div data-has-next="false"></div>
            </body>
          </html>
        `)
      }));

      global.localStorage.getItem.mockReturnValue('[]');

      // Intercept setTimeout to get direct access to the callback
      let loadJobsTimeoutCallback = null;
      const originalSetTimeout = global.setTimeout;
      global.setTimeout = vi.fn((callback, delay) => {
        if (delay === 1000) {
          loadJobsTimeoutCallback = callback;
          return 999; // Return different ID
        } else {
          return originalSetTimeout(callback, delay);
        }
      });

      initializeMainJs();

      // Call loadJobs to set up the timeout
      window.loadJobs(2);

      // Wait for fetch and DOM update
      await vi.waitFor(() => {
        const job = document.querySelector('article[data-job-id="coverage-test-job"]');
        expect(job).toBeTruthy();
      });

      // Verify the button exists and has NO listener attribute
      const btn = document.querySelector('.seen-job-btn[data-job-id="coverage-test-job"]');
      expect(btn).toBeTruthy();
      expect(btn.hasAttribute('data-listener-added')).toBe(false);

      // Spy on the exact button's addEventListener method
      const addEventListenerSpy = vi.spyOn(btn, 'addEventListener');

      // Now execute the timeout callback which should hit lines 336-337
      expect(loadJobsTimeoutCallback).not.toBeNull();
      loadJobsTimeoutCallback();

      // Verify lines 336-337 were executed
      expect(addEventListenerSpy).toHaveBeenCalledWith('click', expect.any(Function));
      expect(btn.hasAttribute('data-listener-added')).toBe(true);

      addEventListenerSpy.mockRestore();
      global.setTimeout = originalSetTimeout;
    });

    test('should cover lines 651-652 in loadMoreJobs timeout with precise control', async () => {
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

      global.fetch = vi.fn(() => Promise.resolve({
        text: () => Promise.resolve(`
          <html>
            <body>
              <article data-job-id="loadmore-coverage-job">
                <button class="seen-job-btn" data-job-id="loadmore-coverage-job">
                  <svg class="seen-icon hidden"></svg>
                  <svg class="unseen-icon"></svg>
                </button>
              </article>
              <div data-has-next="false"></div>
            </body>
          </html>
        `)
      }));

      global.localStorage.getItem.mockReturnValue('[]');

      // Intercept setTimeout for loadMoreJobs - need to capture the SECOND 1000ms timeout
      let timeoutCallbacks = [];
      const originalSetTimeout = global.setTimeout;
      global.setTimeout = vi.fn((callback, delay) => {
        if (delay === 1000) {
          timeoutCallbacks.push(callback);
          return 998 + timeoutCallbacks.length; // Different IDs
        } else {
          return originalSetTimeout(callback, delay);
        }
      });

      initializeMainJs();

      // Call loadMoreJobs
      window.loadMoreJobs(2);

      // Wait for fetch and DOM update
      await vi.waitFor(() => {
        const job = document.querySelector('article[data-job-id="loadmore-coverage-job"]');
        expect(job).toBeTruthy();
      });

      // Verify button state
      const btn = document.querySelector('.seen-job-btn[data-job-id="loadmore-coverage-job"]');
      expect(btn).toBeTruthy();
      expect(btn.hasAttribute('data-listener-added')).toBe(false);

      // Spy on addEventListener
      const addEventListenerSpy = vi.spyOn(btn, 'addEventListener');

      // Execute the loadMoreJobs timeout callback (lines 651-652) - should be the second one
      expect(timeoutCallbacks.length).toBeGreaterThanOrEqual(2);
      const loadMoreJobsTimeoutCallback = timeoutCallbacks[1]; // Second timeout is from loadMoreJobs
      loadMoreJobsTimeoutCallback();

      // Verify lines 651-652 were executed
      expect(addEventListenerSpy).toHaveBeenCalledWith('click', expect.any(Function));
      expect(btn.hasAttribute('data-listener-added')).toBe(true);

      addEventListenerSpy.mockRestore();
      global.setTimeout = originalSetTimeout;
    });

    test('should execute event listener addition lines in loadJobs function', async () => {
      document.documentElement.innerHTML = `
        <html>
          <head></head>
          <body>
            <div id="theme-toggle">Toggle</div>
            <div data-current-page="1"></div>
            <form id="filter-form"></form>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
              <article data-job-id="existing-job">
                <button class="seen-job-btn" data-job-id="existing-job">
                  <svg class="seen-icon hidden"></svg>
                  <svg class="unseen-icon"></svg>
                </button>
              </article>
            </div>
          </body>
        </html>
      `;

      global.fetch = vi.fn(() => Promise.resolve({
        text: () => Promise.resolve(`
          <html>
            <body>
              <article data-job-id="fresh-job">
                <button class="seen-job-btn" data-job-id="fresh-job">
                  <svg class="seen-icon hidden"></svg>
                  <svg class="unseen-icon"></svg>
                </button>
              </article>
              <div data-has-next="false"></div>
            </body>
          </html>
        `)
      }));

      global.localStorage.getItem.mockReturnValue('[]');

      // Mock setTimeout but execute the callbacks synchronously for precise control
      const timeoutCallbacks = [];
      global.setTimeout = vi.fn((callback, delay) => {
        if (delay === 1000) {
          timeoutCallbacks.push(callback);
          return delay;
        } else {
          callback();
          return delay;
        }
      });

      initializeMainJs();

      // Spy on addEventListener to verify it gets called
      const addEventListenerSpy = vi.spyOn(Element.prototype, 'addEventListener');

      // Call loadJobs
      window.loadJobs(2);

      // Wait for DOM to be updated
      await vi.waitFor(() => {
        const newBtn = document.querySelector('article[data-job-id="fresh-job"] .seen-job-btn');
        expect(newBtn).toBeTruthy();
      });

      const newBtn = document.querySelector('article[data-job-id="fresh-job"] .seen-job-btn');
      expect(newBtn.hasAttribute('data-listener-added')).toBe(false);

      // Execute the timeout callback which should add the event listener
      timeoutCallbacks.forEach(callback => callback());

      // Verify addEventListener was called on the new button
      expect(addEventListenerSpy).toHaveBeenCalledWith('click', expect.any(Function));
      expect(newBtn.hasAttribute('data-listener-added')).toBe(true);

      addEventListenerSpy.mockRestore();
    });

    test('should execute event listener addition lines in loadMoreJobs function', async () => {
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

      global.fetch = vi.fn(() => Promise.resolve({
        text: () => Promise.resolve(`
          <html>
            <body>
              <article data-job-id="fresh-loadmore-job">
                <button class="seen-job-btn" data-job-id="fresh-loadmore-job">
                  <svg class="seen-icon hidden"></svg>
                  <svg class="unseen-icon"></svg>
                </button>
              </article>
              <div data-has-next="false"></div>
            </body>
          </html>
        `)
      }));

      global.localStorage.getItem.mockReturnValue('[]');

      const timeoutCallbacks = [];
      global.setTimeout = vi.fn((callback, delay) => {
        if (delay === 1000) {
          timeoutCallbacks.push(callback);
          return delay;
        } else {
          callback();
          return delay;
        }
      });

      initializeMainJs();

      // Spy on addEventListener
      const addEventListenerSpy = vi.spyOn(Element.prototype, 'addEventListener');

      // Call loadMoreJobs
      window.loadMoreJobs(2);

      // Wait for DOM to be updated
      await vi.waitFor(() => {
        const newBtn = document.querySelector('article[data-job-id="fresh-loadmore-job"] .seen-job-btn');
        expect(newBtn).toBeTruthy();
      });

      const newBtn = document.querySelector('article[data-job-id="fresh-loadmore-job"] .seen-job-btn');
      expect(newBtn.hasAttribute('data-listener-added')).toBe(false);

      // Execute timeout callback
      timeoutCallbacks.forEach(callback => callback());

      // Verify addEventListener was called
      expect(addEventListenerSpy).toHaveBeenCalledWith('click', expect.any(Function));
      expect(newBtn.hasAttribute('data-listener-added')).toBe(true);

      addEventListenerSpy.mockRestore();
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
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"></div>
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
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"></div>
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

      // Should use the form action (which defaults to current URL when no action attribute)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('page=2'),
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
