// Map through all incoming items
return $input.all().map(item => {
  const data = item.json;

  // Safely extract URL and Context from the body or root
  const url = data.body?.url || data.url || '';
  const context = data.body?.context || data.context || {};

  // Validation logic
  let validFormat = false;
  let error = null;

  if (!url || url.trim() === '') {
    error = 'URL is required';
  } else if (!url.startsWith('http://') && !url.startsWith('https://')) {
    error = 'URL must start with http:// or https://';
  } else {
    // URL has valid protocol - mark as valid
    validFormat = true;
  }

  // Return in the standard n8n format
  return {
    json: {
      url,
      context,
      validFormat,
      error
    }
  };
});
