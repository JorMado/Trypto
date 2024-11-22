# error_handler.py
from typing import Dict, Optional, Any, Callable
import logging
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class ErrorThresholds:
    max_count: int
    window_seconds: int
    severity: str

class EnhancedErrorHandler:
    def __init__(self):
        # Define error thresholds for different types of errors
        self.error_thresholds = {
            'system': ErrorThresholds(max_count=5, window_seconds=300, severity='critical'),
            'network': ErrorThresholds(max_count=10, window_seconds=60, severity='high'),
            'api': ErrorThresholds(max_count=20, window_seconds=60, severity='medium'),
            'data': ErrorThresholds(max_count=50, window_seconds=300, severity='low'),
            'validation': ErrorThresholds(max_count=100, window_seconds=300, severity='low'),
            'connection': ErrorThresholds(max_count=5, window_seconds=60, severity='high'),
            'blockchain': ErrorThresholds(max_count=10, window_seconds=120, severity='high'),
            'exchange': ErrorThresholds(max_count=15, window_seconds=60, severity='medium'),
            'database': ErrorThresholds(max_count=5, window_seconds=300, severity='critical')
        }
        
        # Initialize error tracking
        self.error_counts = defaultdict(list)
        self.error_handlers = {}
        self.circuit_breakers = {}
        
        # Setup logging
        self.logger = logging.getLogger('ErrorHandler')
        self.logger.setLevel(logging.INFO)
        
    async def handle_error(self, 
                          error_type: str, 
                          error: Exception,
                          context: Optional[Dict] = None) -> None:
        """
        Handle an error with appropriate logging and actions
        
        Args:
            error_type: Type of error (system, network, api, etc.)
            error: The actual error/exception
            context: Optional context information
        """
        try:
            # Ensure error type exists
            if error_type not in self.error_thresholds:
                error_type = 'system'  # Default to system error type
                
            # Record error
            current_time = datetime.now()
            self.error_counts[error_type].append(current_time)
            
            # Clean up old errors
            self._cleanup_old_errors(error_type)
            
            # Get error count in current window
            error_count = len(self.error_counts[error_type])
            threshold = self.error_thresholds[error_type]
            
            # Log error with appropriate severity
            self._log_error(error_type, error, error_count, threshold, context)
            
            # Check if threshold is exceeded
            if error_count >= threshold.max_count:
                await self._handle_threshold_exceeded(error_type, error, context)
                
            # Execute specific error handler if exists
            if error_type in self.error_handlers:
                await self.error_handlers[error_type](error, context)
                
        except Exception as e:
            # If error handling fails, log it and continue
            self.logger.critical(f"Error in error handler: {str(e)}")
            
    def _cleanup_old_errors(self, error_type: str) -> None:
        """Remove errors outside the current window"""
        threshold = self.error_thresholds[error_type]
        cutoff_time = datetime.now() - timedelta(seconds=threshold.window_seconds)
        self.error_counts[error_type] = [
            timestamp for timestamp in self.error_counts[error_type]
            if timestamp > cutoff_time
        ]
        
    def _log_error(self, 
                   error_type: str,
                   error: Exception,
                   count: int,
                   threshold: ErrorThresholds,
                   context: Optional[Dict]) -> None:
        """Log error with appropriate severity"""
        log_message = (
            f"Error Type: {error_type} | "
            f"Count: {count}/{threshold.max_count} | "
            f"Error: {str(error)}"
        )
        
        if context:
            log_message += f" | Context: {context}"
            
        if threshold.severity == 'critical':
            self.logger.critical(log_message)
        elif threshold.severity == 'high':
            self.logger.error(log_message)
        elif threshold.severity == 'medium':
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
            
    async def _handle_threshold_exceeded(self,
                                      error_type: str,
                                      error: Exception,
                                      context: Optional[Dict]) -> None:
        """Handle case where error threshold is exceeded"""
        threshold = self.error_thresholds[error_type]
        
        # Log threshold exceeded
        self.logger.critical(
            f"Error threshold exceeded for {error_type} errors. "
            f"Severity: {threshold.severity}"
        )
        
        # Trigger circuit breaker if exists
        if error_type in self.circuit_breakers:
            await self.circuit_breakers[error_type](error_type, context)
            
        # Take action based on severity
        if threshold.severity == 'critical':
            await self._handle_critical_error(error_type, error, context)
        elif threshold.severity == 'high':
            await self._handle_high_severity_error(error_type, error, context)
            
    async def _handle_critical_error(self,
                                   error_type: str,
                                   error: Exception,
                                   context: Optional[Dict]) -> None:
        """Handle critical errors"""
        self.logger.critical(
            f"Critical error threshold exceeded for {error_type}. "
            f"Initiating emergency procedures."
        )
        # Implement emergency procedures here
        
    async def _handle_high_severity_error(self,
                                        error_type: str,
                                        error: Exception,
                                        context: Optional[Dict]) -> None:
        """Handle high severity errors"""
        self.logger.error(
            f"High severity error threshold exceeded for {error_type}. "
            f"Initiating mitigation procedures."
        )
        # Implement mitigation procedures here
        
    def register_error_handler(self,
                             error_type: str,
                             handler: Callable) -> None:
        """Register a custom error handler for a specific error type"""
        self.error_handlers[error_type] = handler
        
    def register_circuit_breaker(self,
                               error_type: str,
                               circuit_breaker: Callable) -> None:
        """Register a circuit breaker for a specific error type"""
        self.circuit_breakers[error_type] = circuit_breaker
        
    async def get_error_statistics(self) -> Dict[str, Dict]:
        """Get error statistics for monitoring"""
        stats = {}
        for error_type in self.error_thresholds.keys():
            self._cleanup_old_errors(error_type)
            threshold = self.error_thresholds[error_type]
            count = len(self.error_counts[error_type])
            
            stats[error_type] = {
                'count': count,
                'threshold': threshold.max_count,
                'severity': threshold.severity,
                'window_seconds': threshold.window_seconds,
                'percentage': (count / threshold.max_count) * 100
            }
            
        return stats

# Example custom error handlers
async def handle_network_error(error: Exception, context: Optional[Dict]):
    # Implement network error handling
    pass

async def handle_api_error(error: Exception, context: Optional[Dict]):
    # Implement API error handling
    pass

# Example circuit breakers
async def network_circuit_breaker(error_type: str, context: Optional[Dict]):
    # Implement network circuit breaker
    pass

async def api_circuit_breaker(error_type: str, context: Optional[Dict]):
    # Implement API circuit breaker
    pass

# Create and configure error handler
error_handler = EnhancedErrorHandler()
error_handler.register_error_handler('network', handle_network_error)
error_handler.register_error_handler('api', handle_api_error)
error_handler.register_circuit_breaker('network', network_circuit_breaker)
error_handler.register_circuit_breaker('api', api_circuit_breaker)