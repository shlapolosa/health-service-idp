import asyncio
import streamlit as st
from typing import Any, Coroutine, Optional, Callable
import threading
from concurrent.futures import ThreadPoolExecutor
import functools

class StreamlitAsyncRunner:
    """Utility class to run async functions in Streamlit"""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._loop = None
        self._thread = None
        self._start_event_loop()
    
    def _start_event_loop(self):
        """Start the event loop in a separate thread"""
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()
        
        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()
        
        # Wait for loop to be ready
        while self._loop is None:
            pass
    
    def run_async(self, coro: Coroutine) -> Any:
        """Run an async coroutine and return the result"""
        if self._loop is None:
            raise RuntimeError("Event loop not initialized")
        
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=30)  # 30 second timeout
    
    def run_async_with_callback(self, coro: Coroutine, callback: Optional[Callable] = None):
        """Run async coroutine with optional callback"""
        def wrapper():
            try:
                result = self.run_async(coro)
                if callback:
                    callback(result, None)
                return result
            except Exception as e:
                if callback:
                    callback(None, e)
                raise
        
        return self.executor.submit(wrapper)
    
    def cleanup(self):
        """Cleanup resources"""
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=5)
        self.executor.shutdown(wait=True)

# Global async runner instance
async_runner = StreamlitAsyncRunner()

def async_cached(cache_key: str, ttl_seconds: int = 300):
    """Decorator to cache async function results in Streamlit session state"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key with function name and args
            full_cache_key = f"async_cache_{cache_key}_{hash(str(args) + str(kwargs))}"
            
            # Check if cached result exists and is still valid
            if full_cache_key in st.session_state:
                cached_data = st.session_state[full_cache_key]
                import time
                if time.time() - cached_data['timestamp'] < ttl_seconds:
                    return cached_data['result']
            
            # Run async function and cache result
            result = async_runner.run_async(func(*args, **kwargs))
            
            import time
            st.session_state[full_cache_key] = {
                'result': result,
                'timestamp': time.time()
            }
            
            return result
        return wrapper
    return decorator

def run_async_in_streamlit(coro: Coroutine) -> Any:
    """Convenience function to run async code in Streamlit"""
    return async_runner.run_async(coro)

def with_loading_spinner(message: str = "Loading..."):
    """Decorator to show loading spinner while async function runs"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with st.spinner(message):
                return func(*args, **kwargs)
        return wrapper
    return decorator

class AsyncTaskManager:
    """Manages multiple async tasks in Streamlit"""
    
    def __init__(self):
        self.tasks = {}
        self.results = {}
    
    def submit_task(self, task_id: str, coro: Coroutine, callback: Optional[Callable] = None):
        """Submit an async task"""
        def task_callback(result, error):
            self.results[task_id] = {'result': result, 'error': error, 'completed': True}
            if callback:
                callback(result, error)
        
        future = async_runner.run_async_with_callback(coro, task_callback)
        self.tasks[task_id] = future
        self.results[task_id] = {'completed': False}
    
    def get_task_status(self, task_id: str) -> dict:
        """Get status of a task"""
        if task_id not in self.results:
            return {'exists': False}
        
        result_data = self.results[task_id]
        return {
            'exists': True,
            'completed': result_data['completed'],
            'result': result_data.get('result'),
            'error': result_data.get('error')
        }
    
    def wait_for_task(self, task_id: str, timeout: int = 30) -> Any:
        """Wait for a task to complete and return result"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        future = self.tasks[task_id]
        return future.result(timeout=timeout)
    
    def cleanup_completed_tasks(self):
        """Clean up completed tasks"""
        completed_tasks = [
            task_id for task_id, result in self.results.items() 
            if result['completed']
        ]
        
        for task_id in completed_tasks:
            if task_id in self.tasks:
                del self.tasks[task_id]
            del self.results[task_id]

# Global task manager
task_manager = AsyncTaskManager()