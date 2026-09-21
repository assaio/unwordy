function retry(fn) {
  // The rate limiter needs a pause before the second call.
  return fn();
}
