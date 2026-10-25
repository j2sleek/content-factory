/**
 * Content Factory - Apps Script Pub/Sub Router
 * Orchestrates pipeline stages via webhooks
 */

const PROPS = PropertiesService.getScriptProperties();

/**
 * Webhook endpoint for pub/sub routing
 */
function doPost(e) {
  const lock = LockService.getScriptLock();
  try {
    // Wait up to 30 seconds for lock
    lock.waitLock(30000);
    
    const data = JSON.parse(e.postData.contents);
    const ss = SpreadsheetApp.openById(PROPS.getProperty('SHEET_ID'));
    
    // Log to pipeline state
    logPipelineState(ss, data);
    
    // Write items to sheet if present
    if (data.items && Array.isArray(data.items) && data.items.length > 0) {
      writeItemsToSheet(ss, data.stage, data.items);
    }
    
    // Route to next stage if completed
    if (data.status === 'completed') {
      routeToNextStage(ss, data);
    }
    
    return ContentService
      .createTextOutput(JSON.stringify({ success: true, run_id: data.run_id }))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    console.error('Router error:', error);
    return ContentService
      .createTextOutput(JSON.stringify({ success: false, error: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}

/**
 * Log pipeline state
 */
function logPipelineState(ss, data) {
  let sheet = ss.getSheetByName('pipeline_state');
  if (!sheet) {
    sheet = ss.insertSheet('pipeline_state');
    sheet.appendRow(['Timestamp', 'Run ID', 'Stage', 'Status', 'Count', 'Source']);
    sheet.getRange(1, 1, 1, 6).setFontWeight('bold');
  }
  
  sheet.appendRow([
    new Date(),
    data.run_id || '',
    data.stage || '',
    data.status || '',
    data.count || (data.items ? data.items.length : 0),
    data.source || ''
  ]);
}

/**
 * Write items to appropriate sheet
 */
function writeItemsToSheet(ss, stage, items) {
  let sheetName;
  if (stage === 'scraper') {
    sheetName = 'raw_deals';
  } else if (stage === 'normalizer') {
    sheetName = 'normalized_deals';
  } else if (stage === 'ai') {
    return; // AI writes to specific content sheets
  } else {
    sheetName = 'raw_deals';
  }
  
  let sheet = ss.getSheetByName(sheetName);
  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
    // Add headers
    if (sheetName === 'raw_deals') {
      sheet.appendRow([
        'ID', 'Source', 'Title', 'URL', 'Summary', 'Published At', 
        'Scraped At', 'Amount', 'Currency', 'Amount USD', 'Round', 
        'Countries', 'Sector', 'Investors', 'Status', 'Run ID'
      ]);
    } else if (sheetName === 'normalized_deals') {
      sheet.appendRow([
        'ID', 'Source', 'Title', 'URL', 'Summary', 'Published At',
        'Amount', 'Currency', 'Amount USD', 'Round', 'Countries', 
        'Sector', 'Investors', 'Startup Name', 'Status', 'Normalized At', 'Run ID'
      ]);
    }
    sheet.getRange(1, 1, 1, sheet.getLastColumn()).setFontWeight('bold');
  }
  
  // Get existing IDs to avoid duplicates
  const existingIds = new Set();
  const lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    const idRange = sheet.getRange(2, 1, lastRow - 1, 1).getValues();
    idRange.forEach(row => {
      if (row[0]) existingIds.add(row[0].toString());
    });
  }
  
  items.forEach(item => {
    if (existingIds.has(item.id)) {
      return; // Skip duplicates
    }
    
    if (sheetName === 'raw_deals') {
      sheet.appendRow([
        item.id || '',
        item.source || '',
        item.title || '',
        item.url || '',
        item.summary || '',
        item.published_at || '',
        item.scraped_at || '',
        item.amount || '',
        item.currency || '',
        item.amount_usd || '',
        item.round || '',
        item.countries || '',
        item.sector || '',
        item.investors || '',
        'new',
        data.run_id || ''
      ]);
    } else if (sheetName === 'normalized_deals') {
      sheet.appendRow([
        item.id || '',
        item.source || '',
        item.title || '',
        item.url || '',
        item.summary || '',
        item.published_at || '',
        item.amount || '',
        item.currency || '',
        item.amount_usd || '',
        item.round || '',
        item.countries || '',
        item.sector || '',
        item.startup_name || '',
        item.status || 'normalized',
        item.normalized_at || new Date().toISOString(),
        data.run_id || ''
      ]);
    }
  });
}

/**
 * Route to next stage
 */
function routeToNextStage(ss, data) {
  const runId = data.run_id;
  const stage = data.stage;
  
  if (stage === 'scraper') {
    const normalizerUrl = PROPS.getProperty('NORMALIZER_WEBHOOK_URL');
    if (normalizerUrl && data.count > 0) {
      const payload = {
        stage: 'normalizer_trigger',
        run_id: runId,
        triggered_by: 'scraper',
        items: data.items || []
      };
      
      try {
        UrlFetchApp.fetch(normalizerUrl, {
          method: 'post',
          contentType: 'application/json',
          payload: JSON.stringify(payload),
          muteHttpExceptions: true
        });
        console.log('Triggered normalizer for run:', runId);
      } catch (e) {
        console.error('Failed to trigger normalizer:', e);
      }
    }
  } else if (stage === 'normalizer') {
    const opencodeUrl = PROPS.getProperty('OPENCODE_TRIGGER_URL');
    if (opencodeUrl && data.count > 0) {
      const payload = {
        stage: 'ai_trigger',
        run_id: runId,
        triggered_by: 'normalizer',
        count: data.count
      };
      
      try {
        UrlFetchApp.fetch(opencodeUrl, {
          method: 'post',
          contentType: 'application/json',
          payload: JSON.stringify(payload),
          muteHttpExceptions: true
        });
        console.log('Triggered opencode for run:', runId);
      } catch (e) {
        console.error('Failed to trigger opencode:', e);
      }
    }
  }
}

/**
 * Manual trigger for testing
 */
function testScraper() {
  const scraperUrl = PROPS.getProperty('SCRAPER_WEBHOOK_URL');
  if (scraperUrl) {
    UrlFetchApp.fetch(scraperUrl, {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify({ test: true }),
      muteHttpExceptions: true
    });
  }
}

/**
 * Setup function - run once to create sheets
 */
function setupSheets() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheets = ['raw_deals', 'normalized_deals', 'shorts_scripts', 'weekly_roundup', 'pipeline_state', 'errors'];
  
  sheets.forEach(name => {
    if (!ss.getSheetByName(name)) {
      ss.insertSheet(name);
    }
  });
  
  // Setup headers
  const rawSheet = ss.getSheetByName('raw_deals');
  if (rawSheet.getLastRow() === 0) {
    rawSheet.appendRow(['ID', 'Source', 'Title', 'URL', 'Summary', 'Published At', 
      'Scraped At', 'Amount', 'Currency', 'Amount USD', 'Round', 
      'Countries', 'Sector', 'Investors', 'Status', 'Run ID']);
    rawSheet.getRange(1, 1, 1, 16).setFontWeight('bold');
  }
  
  const shortsSheet = ss.getSheetByName('shorts_scripts');
  if (shortsSheet.getLastRow() === 0) {
    shortsSheet.appendRow(['Deal ID', 'Platform', 'Hook', 'Script', 'Caption', 'Hashtags', 
      'Visual Cues', 'Voiceover Text', 'Duration (sec)', 'Status', 'Generated At']);
    shortsSheet.getRange(1, 1, 1, 11).setFontWeight('bold');
  }
  
  const weeklySheet = ss.getSheetByName('weekly_roundup');
  if (weeklySheet.getLastRow() === 0) {
    weeklySheet.appendRow(['Week Starting', 'Title', 'Intro', 'Deals Section', 'Trends', 
      'Outro', 'Full Script', 'Timestamps', 'Status', 'Generated At']);
    weeklySheet.getRange(1, 1, 1, 10).setFontWeight('bold');
  }
}
