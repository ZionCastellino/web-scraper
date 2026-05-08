import { useState } from 'react'
import { Link, Search, Download, AlertCircle, Sparkles, Database, FileText, FileJson, Table } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import './index.css'

function App() {
  const [url, setUrl] = useState('')
  const [prompt, setPrompt] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [data, setData] = useState(null)

  const handleScrape = async (e) => {
    e.preventDefault()
    if (!url) {
      setError('Please enter a valid URL.')
      return
    }

    setError('')
    setIsLoading(true)
    setData(null)

    try {
      const response = await fetch('/api/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, prompt: prompt || 'Extract all meaningful data as structured JSON' })
      })

      const result = await response.json()

      if (result.success) {
        setData(result.data)
      } else {
        setError(result.error || 'An unknown error occurred.')
      }
    } catch (err) {
      setError('Failed to connect to the server. ' + err.message)
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleExport = async (format) => {
    if (!data || data.length === 0) return

    try {
      const response = await fetch('/api/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data, format })
      })

      if (!response.ok) throw new Error('Download failed')

      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = downloadUrl

      const cd = response.headers.get('Content-Disposition')
      let filename = `scraped_data.${format}`
      if (cd && cd.includes('filename=')) {
        filename = cd.split('filename=')[1].replace(/"/g, '')
      }

      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(downloadUrl)
    } catch (err) {
      setError('Failed to download file.')
      console.error(err)
    }
  }

  const getHeaders = () => {
    if (!data || data.length === 0) return []
    const keys = new Set()
    data.forEach(item => {
      if (typeof item === 'object' && item !== null) {
        Object.keys(item).forEach(k => keys.add(k))
      }
    })
    return Array.from(keys)
  }

  const headers = getHeaders()

  return (
    <div className="app-container">
      <div className="bg-orb orb-1"></div>
      <div className="bg-orb orb-2"></div>
      <div className="bg-orb orb-3"></div>

      <header>
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h1>AI Web Scraper</h1>
          <p className="subtitle">Intelligently extract structured data from any website.</p>
        </motion.div>
      </header>

      <motion.main 
        className="glass-panel"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <form onSubmit={handleScrape}>
          <div className="form-group">
            <label htmlFor="url">Website URL</label>
            <div className="input-wrapper">
              <Link className="input-icon" size={20} />
              <input
                type="url"
                id="url"
                placeholder="https://example.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="prompt">What do you want to extract?</label>
            <div className="input-wrapper">
              <Sparkles className="input-icon" size={20} />
              <input
                type="text"
                id="prompt"
                placeholder="e.g. Extract product names, prices and descriptions"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
              />
            </div>
          </div>

          <AnimatePresence>
            {error && (
              <motion.div 
                className="alert alert-error"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                <AlertCircle size={20} />
                <span>{error}</span>
              </motion.div>
            )}
          </AnimatePresence>

          <button 
            type="submit" 
            className="btn btn-primary"
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <div className="loader"></div>
                <span>Scraping...</span>
              </>
            ) : (
              <>
                <Search size={20} />
                <span>Scrape Data</span>
              </>
            )}
          </button>
        </form>

        <AnimatePresence>
          {data && (
            <motion.div 
              className="results-container"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <div className="results-header">
                <h2>Extracted Data</h2>
                <div className="export-actions">
                  <button type="button" className="btn btn-secondary" onClick={() => handleExport('json')}>
                    <FileJson size={16} /> JSON
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={() => handleExport('csv')}>
                    <Table size={16} /> CSV
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={() => handleExport('md')}>
                    <FileText size={16} /> MD
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={() => handleExport('txt')}>
                    <Database size={16} /> TXT
                  </button>
                </div>
              </div>

              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      {headers.length > 0 ? (
                        headers.map(h => (
                          <th key={h}>{h.charAt(0).toUpperCase() + h.slice(1)}</th>
                        ))
                      ) : (
                        <th>No data found</th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((item, index) => (
                      <tr key={index}>
                        {headers.map(h => {
                          const val = item ? item[h] : '';
                          return (
                            <td key={h}>
                              {(val !== null && val !== undefined) ? String(val) : '-'}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.main>
    </div>
  )
}

export default App
