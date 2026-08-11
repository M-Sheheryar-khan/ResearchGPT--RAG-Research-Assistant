import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ForceGraph2D from "react-force-graph-2d";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid
} from "recharts";
import "./App.css";

function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pdf, setPdf] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [pdfList, setPdfList] = useState([]);
  const [similarMap, setSimilarMap] = useState({});
  const [similarLoading, setSimilarLoading] = useState({});
  const [stats, setStats] = useState(null);
  const [statsOpen, setStatsOpen] = useState(false);
  const [networkData, setNetworkData] = useState(null);
  const [networkLoading, setNetworkLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);

  async function loadPdfList() {
    try {
      const response = await axios.get("http://127.0.0.1:8000/pdfs");
      setPdfList(response.data.pdfs);
    } catch (error) {
      console.error(error);
    }
  }

  async function loadStats() {
    try {
      const response = await axios.get("http://127.0.0.1:8000/stats");
      setStats(response.data);
    } catch (error) {
      console.error(error);
    }
  }

  async function loadNetwork() {
    setNetworkLoading(true);
    try {
      const response = await axios.get("http://127.0.0.1:8000/network");
      setNetworkData(response.data);
    } catch (error) {
      console.error(error);
    }
    setNetworkLoading(false);
  }

  useEffect(() => {
    loadPdfList();
    loadStats();
    loadNetwork();
  }, []);

  async function askQuestion() {
    if (!question.trim()) return;

    setLoading(true);
    setAnswer("");
    setSources([]);
    setSimilarMap({});

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/ask?question=${encodeURIComponent(question)}`
      );

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = "";
      let sourcesParsed = false;
      let accumulatedAnswer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        if (!sourcesParsed) {
          const newlineIndex = buffer.indexOf("\n");
          if (newlineIndex !== -1) {
            const sourcesLine = buffer.slice(0, newlineIndex);

            if (sourcesLine.startsWith("SOURCES::")) {
              try {
                setSources(JSON.parse(sourcesLine.replace("SOURCES::", "")));
              } catch (e) {
                console.error("Failed to parse sources", e);
              }
            }

            buffer = buffer.slice(newlineIndex + 1);
            sourcesParsed = true;
            setLoading(false);

            accumulatedAnswer += buffer;
            setAnswer(accumulatedAnswer);
            buffer = "";
          }
        } else {
          accumulatedAnswer += buffer;
          setAnswer(accumulatedAnswer);
          buffer = "";
        }
      }
    } catch (error) {
      setAnswer("Error connecting to backend.");
      console.error(error);
    }

    setLoading(false);
  }

  async function uploadPDF(){
    if (!pdf) return;

    const formData = new FormData();
    formData.append("file", pdf);

    setUploadStatus(null);

    try{
      const response = await axios.post(
        "http://127.0.0.1:8000/upload",
        formData
      );

      setUploadStatus({
        success: true,
        usedOcr: response.data.used_ocr,
        chunks: response.data.chunks
      });

      setPdf(null);
      loadPdfList();
      loadStats();
      loadNetwork();
    } catch(error){
      console.error(error);
      setUploadStatus({ success: false });
    }
  }

  async function deletePDF(filename) {
    const confirmed = window.confirm(`Delete "${filename}"? This can't be undone.`);
    if (!confirmed) return;

    try {
      await axios.delete(`http://127.0.0.1:8000/pdfs/${encodeURIComponent(filename)}`);
      loadPdfList();
      loadStats();
      loadNetwork();
    } catch (error) {
      console.error(error);
      alert("Failed to delete PDF.");
    }
  }

  async function loadSimilar(title) {
    if (similarMap[title]) {
      setSimilarMap((prev) => {
        const updated = { ...prev };
        delete updated[title];
        return updated;
      });
      return;
    }

    setSimilarLoading((prev) => ({ ...prev, [title]: true }));

    try {
      const response = await axios.get(
        `http://127.0.0.1:8000/similar?title=${encodeURIComponent(title)}`
      );

      setSimilarMap((prev) => ({
        ...prev,
        [title]: response.data.recommendations
      }));
    } catch (error) {
      console.error(error);
    }

    setSimilarLoading((prev) => ({ ...prev, [title]: false }));
  }

  const handleNodeClick = useCallback((node) => {
    setSelectedNode(node);
  }, []);

  return (
    <div className="app">
      <div className="pageShell">

        <div className="topBar">
          <h1 className="wordmark">ResearchGPT</h1>
          <span className="eyebrow">Local RAG Research Assistant</span>
        </div>

        <div className="layoutGrid">

          <div className="mainColumn">

            <div className="card">
              <div className="inputBox">
                <input
                  type="text"
                  placeholder="Ask a research question..."
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && askQuestion()}
                />

                <button
                  onClick={askQuestion}
                  disabled={loading}
                >
                  {loading ? "Thinking..." : "Ask"}
                </button>
              </div>
            </div>

            <div className="card">
              <h2>Add a document</h2>
              <div className="uploadBox">
                <div>
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={(e) => {
                      setPdf(e.target.files[0]);
                      setUploadStatus(null);
                    }}
                  />

                  <button onClick={uploadPDF}>
                    Upload PDF
                  </button>
                </div>

                {uploadStatus && (
                  uploadStatus.success ? (
                    <p className="uploadNote">
                      ✅ Uploaded ({uploadStatus.chunks} chunks) —{" "}
                      {uploadStatus.usedOcr
                        ? "📷 scanned document, extracted via OCR"
                        : "📝 text extracted directly"}
                    </p>
                  ) : (
                    <p className="uploadNote uploadError">
                      ❌ Upload failed. Please try again.
                    </p>
                  )
                )}
              </div>
            </div>

            {stats && (
              <div className="card">
                <button
                  className="statsToggle"
                  onClick={() => setStatsOpen(!statsOpen)}
                >
                  <span>Research Trends</span>
                  <span>{statsOpen ? "−" : "+"}</span>
                </button>

                {statsOpen && (
                  <div className="statsContent">
                    <div className="statsSummary">
                      <div className="statPill">
                        <span className="statNumber">{stats.total_documents}</span>
                        <span className="statLabel">Total</span>
                      </div>
                      <div className="statPill">
                        <span className="statNumber">{stats.papers}</span>
                        <span className="statLabel">Papers</span>
                      </div>
                      <div className="statPill">
                        <span className="statNumber">{stats.pdfs}</span>
                        <span className="statLabel">Uploaded</span>
                      </div>
                    </div>

                    {stats.by_year.length > 0 && (
                      <div className="chartBlock">
                        <h3>Papers by Year</h3>
                        <ResponsiveContainer width="100%" height={180}>
                          <BarChart data={stats.by_year}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(201,162,75,0.08)" />
                            <XAxis dataKey="year" stroke="#6B7570" fontSize={11} />
                            <YAxis stroke="#6B7570" fontSize={11} allowDecimals={false} />
                            <Tooltip
                              contentStyle={{ background: "#0F1916", border: "1px solid rgba(201,162,75,0.2)", borderRadius: 6 }}
                              labelStyle={{ color: "#EDE8DE" }}
                            />
                            <Bar dataKey="count" fill="#C9A24B" radius={[3, 3, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    )}

                    {stats.top_keywords.length > 0 && (
                      <div className="chartBlock">
                        <h3>Top Keywords</h3>
                        <ResponsiveContainer width="100%" height={200}>
                          <BarChart data={stats.top_keywords} layout="vertical">
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(201,162,75,0.08)" />
                            <XAxis type="number" stroke="#6B7570" fontSize={11} allowDecimals={false} />
                            <YAxis
                              type="category"
                              dataKey="keyword"
                              stroke="#6B7570"
                              fontSize={11}
                              width={100}
                            />
                            <Tooltip
                              contentStyle={{ background: "#0F1916", border: "1px solid rgba(201,162,75,0.2)", borderRadius: 6 }}
                              labelStyle={{ color: "#EDE8DE" }}
                            />
                            <Bar dataKey="count" fill="#5B8C7B" radius={[0, 3, 3, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    )}

                    {stats.by_year.length === 0 && stats.top_keywords.length === 0 && (
                      <p className="statsEmpty">Not enough metadata yet to show trends.</p>
                    )}
                  </div>
                )}
              </div>
            )}

            {pdfList.length > 0 && (
              <div className="card">
                <h2>Uploaded Documents</h2>

                {pdfList.map((p, i) => (
                  <div key={i} className="pdfRow">
                    <div className="pdfRowInfo">
                      <strong>{p.title}</strong>
                      <span>
                        {p.authors && p.authors !== "Unknown" ? p.authors : "Unknown Authors"}
                        {p.year && p.year !== "Unknown" ? ` · ${p.year}` : ""}
                      </span>
                    </div>

                    <div className="pdfRowActions">
                      {p.url && (
                        <a href={p.url} target="_blank" rel="noreferrer">Open</a>
                      )}
                      <button
                        className="deleteButton"
                        onClick={() => deletePDF(p.title)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {answer && (
              <div className="card">
                <h2>Answer</h2>
                <div className="answerBox">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {answer}
                  </ReactMarkdown>
                </div>
              </div>
            )}

            {sources.length > 0 && (
              <div className="card">
                <h2>Sources</h2>

                {sources.map((s, i) => {
                  const isPdf = s.metadata?.type === "pdf";
                  const title = s.metadata?.title;

                  return (
                    <div key={i} className="sourceCard">
                      <strong>{title || "Untitled"}</strong>

                      <p>
                        {
                        Array.isArray(s.metadata?.authors)
                          ? s.metadata.authors.join(", ")
                          : s.metadata?.authors || "Unknown Authors"
                        }
                        {" "}
                        {s.metadata?.year && s.metadata.year !== "Unknown"
                          ? `(${s.metadata.year})`
                          : ""}
                      </p>

                      {!isPdf && (
                        <>
                          <p>
                            <strong>Journal:</strong>{" "}
                            {s.metadata?.journal || "Unknown"}
                          </p>

                          <p>
                            <strong>Citations:</strong>{" "}
                            {s.metadata?.citations ?? 0}
                          </p>
                        </>
                      )}

                      {isPdf && (
                        <p className="pdfTag">Uploaded document</p>
                      )}

                      <div className="sourceCardActions">
                        {s.metadata?.url && (
                          <a
                            href={s.metadata.url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {isPdf ? "OPEN PDF" : "OPEN PAPER"}
                          </a>
                        )}

                        {title && (
                          <button
                            className="similarButton"
                            onClick={() => loadSimilar(title)}
                          >
                            {similarMap[title] ? "HIDE SIMILAR" : "YOU MIGHT ALSO LIKE"}
                          </button>
                        )}
                      </div>

                      {similarLoading[title] && (
                        <p className="similarLoading">Finding similar papers...</p>
                      )}

                      {similarMap[title] && (
                        <div className="similarBox">
                          {similarMap[title].length === 0 ? (
                            <p className="similarEmpty">No similar papers found.</p>
                          ) : (
                            similarMap[title].map((rec, j) => (
                              <div key={j} className="similarItem">
                                <span className="similarTitle">{rec.title}</span>
                                <span className="similarMeta">
                                  {rec.authors && rec.authors !== "Unknown" ? rec.authors : "Unknown Authors"}
                                  {rec.year && rec.year !== "Unknown" ? ` (${rec.year})` : ""}
                                </span>
                                {rec.url && (
                                  <a href={rec.url} target="_blank" rel="noreferrer">
                                    Open →
                                  </a>
                                )}
                              </div>
                            ))
                          )}
                        </div>
                      )}

                    </div>
                  );
                })}
              </div>
            )}

          </div>

          <div className="sidebarColumn">
            <div className="atlasCard">
              <div className="atlasHeader">
                <h2 className="atlasTitle">Citation Atlas</h2>
                <span className="atlasSubtitle">
                  Documents connected by semantic similarity. Click a node to inspect it.
                </span>
              </div>

              {networkLoading && (
                <p className="networkLoading">Building network graph...</p>
              )}

              {!networkLoading && networkData && networkData.nodes.length > 1 && (
                <div className="networkGraphWrapper">
                  <ForceGraph2D
                    graphData={networkData}
                    nodeId="id"
                    nodeLabel="id"
                    nodeColor={(node) => node.type === "pdf" ? "#5B8C7B" : "#C9A24B"}
                    linkColor={() => "rgba(201,162,75,0.2)"}
                    linkWidth={(link) => Math.max(1, link.value * 3)}
                    backgroundColor="#0F1916"
                    height={420}
                    width={328}
                    onNodeClick={handleNodeClick}
                    nodeRelSize={4}
                  />
                </div>
              )}

              {!networkLoading && networkData && networkData.nodes.length <= 1 && (
                <p className="networkEmpty">
                  Add more documents to see the network graph.
                </p>
              )}

              {selectedNode && (
                <div className="networkSelected">
                  <strong>{selectedNode.id}</strong>
                  <span className="networkSelectedMeta">
                    {selectedNode.type === "pdf" ? "Uploaded document" : "Research paper"}
                    {selectedNode.year && selectedNode.year !== "Unknown" ? ` · ${selectedNode.year}` : ""}
                  </span>
                  <button
                    className="similarButton"
                    onClick={() => {
                      setQuestion(selectedNode.id);
                      setSelectedNode(null);
                    }}
                  >
                    ASK ABOUT THIS
                  </button>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

export default App;