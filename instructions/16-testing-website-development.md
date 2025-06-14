# 16 - Testing Website Development

## Objective
Create an interactive web application that allows users to test the NBA Play-by-Play API and MCP server functionality through a user-friendly interface, serving as both a testing tool and a showcase of capabilities.

## Background
A testing website will provide developers and potential users with an easy way to explore the API functionality, understand data structures, and validate their integration approaches without writing code.

## Scope
- **Interactive API Testing**: Query builder and response viewer
- **MCP Demonstration**: Natural language query interface
- **Data Visualization**: Charts and graphs for API responses
- **Documentation Integration**: Live examples with copy-paste code

## Implementation Plan

### Phase 1: Frontend Framework Setup
1. **Technology stack selection**
   ```javascript
   // React with TypeScript for type safety
   {
     "dependencies": {
       "react": "^18.2.0",
       "typescript": "^5.0.0",
       "@mui/material": "^5.14.0",
       "@emotion/react": "^11.11.0",
       "axios": "^1.4.0",
       "react-query": "^3.39.0",
       "recharts": "^2.8.0",
       "monaco-editor": "^0.40.0",
       "prismjs": "^1.29.0"
     }
   }
   ```

2. **Project structure**
   ```
   src/
   ├── components/
   │   ├── ApiExplorer/
   │   │   ├── QueryBuilder.tsx
   │   │   ├── ResponseViewer.tsx
   │   │   └── EndpointSelector.tsx
   │   ├── McpDemo/
   │   │   ├── NaturalLanguageQuery.tsx
   │   │   └── QueryHistory.tsx
   │   ├── DataVisualization/
   │   │   ├── StatsChart.tsx
   │   │   ├── ShotChart.tsx
   │   │   └── TimelineChart.tsx
   │   └── Common/
   │       ├── Header.tsx
   │       ├── Sidebar.tsx
   │       └── CodeSnippet.tsx
   ├── services/
   │   ├── apiService.ts
   │   └── mcpService.ts
   ├── types/
   │   ├── api.ts
   │   └── mcp.ts
   └── pages/
       ├── ApiTesting.tsx
       ├── McpDemo.tsx
       ├── Examples.tsx
       └── Documentation.tsx
   ```

### Phase 2: API Explorer Interface
1. **Query builder component**
   ```typescript
   interface QueryBuilderProps {
     onQuerySubmit: (query: ApiQuery) => void;
   }
   
   interface ApiQuery {
     endpoint: string;
     method: 'GET' | 'POST';
     parameters: Record<string, any>;
     headers: Record<string, string>;
   }
   
   const QueryBuilder: React.FC<QueryBuilderProps> = ({ onQuerySubmit }) => {
     const [selectedEndpoint, setSelectedEndpoint] = useState('/games');
     const [parameters, setParameters] = useState({});
     const [apiKey, setApiKey] = useState('');
     
     const endpoints = [
       {
         path: '/games',
         description: 'Get NBA games with optional filtering',
         parameters: [
           { name: 'date', type: 'string', description: 'Game date (YYYY-MM-DD)' },
           { name: 'season', type: 'string', description: 'Season (YYYY-YY)' },
           { name: 'team', type: 'string', description: 'Team abbreviation' },
           { name: 'limit', type: 'number', description: 'Number of results' }
         ]
       },
       {
         path: '/players/{player_id}/stats',
         description: 'Get player statistics',
         parameters: [
           { name: 'player_id', type: 'number', required: true },
           { name: 'season', type: 'string', description: 'Season filter' }
         ]
       }
     ];
     
     return (
       <Card>
         <CardContent>
           <Typography variant="h6">API Query Builder</Typography>
           <FormControl fullWidth margin="normal">
             <InputLabel>Endpoint</InputLabel>
             <Select
               value={selectedEndpoint}
               onChange={(e) => setSelectedEndpoint(e.target.value)}
             >
               {endpoints.map(endpoint => (
                 <MenuItem key={endpoint.path} value={endpoint.path}>
                   {endpoint.path}
                 </MenuItem>
               ))}
             </Select>
           </FormControl>
           
           <TextField
             fullWidth
             margin="normal"
             label="API Key"
             type="password"
             value={apiKey}
             onChange={(e) => setApiKey(e.target.value)}
             helperText="Enter your API key to test authenticated endpoints"
           />
           
           {/* Dynamic parameter inputs based on selected endpoint */}
           {renderParameterInputs(selectedEndpoint, parameters, setParameters)}
           
           <Button
             variant="contained"
             onClick={() => onQuerySubmit({
               endpoint: selectedEndpoint,
               method: 'GET',
               parameters,
               headers: { 'X-API-Key': apiKey }
             })}
             disabled={!apiKey}
           >
             Send Request
           </Button>
         </CardContent>
       </Card>
     );
   };
   ```

2. **Response viewer component**
   ```typescript
   interface ResponseViewerProps {
     response: ApiResponse | null;
     loading: boolean;
     error: string | null;
   }
   
   const ResponseViewer: React.FC<ResponseViewerProps> = ({ response, loading, error }) => {
     const [viewMode, setViewMode] = useState<'json' | 'table' | 'chart'>('json');
     
     return (
       <Card>
         <CardContent>
           <Box display="flex" justifyContent="space-between" alignItems="center">
             <Typography variant="h6">Response</Typography>
             <ToggleButtonGroup
               value={viewMode}
               exclusive
               onChange={(_, newMode) => newMode && setViewMode(newMode)}
             >
               <ToggleButton value="json">JSON</ToggleButton>
               <ToggleButton value="table">Table</ToggleButton>
               <ToggleButton value="chart">Chart</ToggleButton>
             </ToggleButtonGroup>
           </Box>
           
           {loading && <CircularProgress />}
           {error && <Alert severity="error">{error}</Alert>}
           
           {response && (
             <>
               <ResponseMetadata response={response} />
               {viewMode === 'json' && <JsonViewer data={response.data} />}
               {viewMode === 'table' && <DataTable data={response.data} />}
               {viewMode === 'chart' && <DataChart data={response.data} />}
               <CodeGenerator query={response.query} language="python" />
             </>
           )}
         </CardContent>
       </Card>
     );
   };
   ```

### Phase 3: MCP Demo Interface
1. **Natural language query component**
   ```typescript
   const McpDemo: React.FC = () => {
     const [query, setQuery] = useState('');
     const [conversation, setConversation] = useState<ConversationItem[]>([]);
     const [loading, setLoading] = useState(false);
     
     const exampleQueries = [
       "What are LeBron James' career averages?",
       "Show me the Lakers vs Celtics game from February 1, 2024",
       "Which player scored the most points in a single game?",
       "How did Stephen Curry perform in the 2022 playoffs?",
       "Compare Michael Jordan and Kobe Bryant's scoring averages"
     ];
     
     const handleSubmit = async () => {
       if (!query.trim()) return;
       
       setLoading(true);
       const userMessage = { type: 'user', content: query, timestamp: new Date() };
       setConversation(prev => [...prev, userMessage]);
       
       try {
         const response = await mcpService.queryNBAData(query);
         const aiMessage = {
           type: 'assistant',
           content: response.content,
           data: response.data,
           timestamp: new Date()
         };
         setConversation(prev => [...prev, aiMessage]);
       } catch (error) {
         const errorMessage = {
           type: 'error',
           content: 'Sorry, I encountered an error processing your query.',
           timestamp: new Date()
         };
         setConversation(prev => [...prev, errorMessage]);
       } finally {
         setLoading(false);
         setQuery('');
       }
     };
     
     return (
       <Box>
         <Typography variant="h4" gutterBottom>
           NBA Data MCP Demo
         </Typography>
         
         <Card sx={{ mb: 3 }}>
           <CardContent>
             <Typography variant="h6" gutterBottom>
               Try asking questions about NBA data in natural language:
             </Typography>
             <Box display="flex" gap={1} flexWrap="wrap" mb={2}>
               {exampleQueries.map((example, index) => (
                 <Chip
                   key={index}
                   label={example}
                   onClick={() => setQuery(example)}
                   variant="outlined"
                   size="small"
                 />
               ))}
             </Box>
           </CardContent>
         </Card>
         
         <Paper sx={{ height: 400, overflow: 'auto', mb: 2, p: 2 }}>
           <ConversationView conversation={conversation} />
         </Paper>
         
         <Box display="flex" gap={1}>
           <TextField
             fullWidth
             placeholder="Ask a question about NBA data..."
             value={query}
             onChange={(e) => setQuery(e.target.value)}
             onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
           />
           <Button
             variant="contained"
             onClick={handleSubmit}
             disabled={loading || !query.trim()}
           >
             {loading ? <CircularProgress size={24} /> : 'Ask'}
           </Button>
         </Box>
       </Box>
     );
   };
   ```

### Phase 4: Data Visualization Components
1. **Statistics charts**
   ```typescript
   interface StatsChartProps {
     data: PlayerStats[] | TeamStats[];
     chartType: 'bar' | 'line' | 'radar';
     metric: string;
   }
   
   const StatsChart: React.FC<StatsChartProps> = ({ data, chartType, metric }) => {
     const chartData = useMemo(() => {
       return data.map(item => ({
         name: item.player_name || item.team_name,
         value: item[metric],
         ...item
       }));
     }, [data, metric]);
     
     if (chartType === 'bar') {
       return (
         <ResponsiveContainer width="100%" height={300}>
           <BarChart data={chartData}>
             <CartesianGrid strokeDasharray="3 3" />
             <XAxis dataKey="name" />
             <YAxis />
             <Tooltip />
             <Bar dataKey="value" fill="#1976d2" />
           </BarChart>
         </ResponsiveContainer>
       );
     }
     
     // Additional chart types...
   };
   ```

2. **Shot chart visualization**
   ```typescript
   const ShotChart: React.FC<{ shots: ShotEvent[] }> = ({ shots }) => {
     const courtDimensions = { width: 500, height: 470 };
     
     return (
       <svg width={courtDimensions.width} height={courtDimensions.height}>
         {/* NBA court background */}
         <CourtBackground />
         
         {/* Shot markers */}
         {shots.map(shot => (
           <circle
             key={shot.shot_id}
             cx={shot.shot_x + 250} // Center court
             cy={shot.shot_y + 50}
             r={4}
             fill={shot.shot_made ? '#4caf50' : '#f44336'}
             opacity={0.7}
           />
         ))}
         
         {/* Legend */}
         <g transform="translate(20, 20)">
           <circle cx={0} cy={0} r={4} fill="#4caf50" />
           <text x={10} y={5} fontSize="12">Made Shot</text>
           <circle cx={0} cy={20} r={4} fill="#f44336" />
           <text x={10} y={25} fontSize="12">Missed Shot</text>
         </g>
       </svg>
     );
   };
   ```

### Phase 5: Code Generation and Examples
1. **Code snippet generator**
   ```typescript
   interface CodeGeneratorProps {
     query: ApiQuery;
     language: 'python' | 'javascript' | 'curl';
   }
   
   const CodeGenerator: React.FC<CodeGeneratorProps> = ({ query, language }) => {
     const generateCode = (query: ApiQuery, lang: string): string => {
       const { endpoint, parameters, headers } = query;
       const queryString = new URLSearchParams(parameters).toString();
       const fullUrl = `https://api.nba-pbp.com/v1${endpoint}${queryString ? '?' + queryString : ''}`;
       
       switch (lang) {
         case 'python':
           return `import requests
   
   headers = ${JSON.stringify(headers, null, 2)}
   response = requests.get("${fullUrl}", headers=headers)
   data = response.json()
   print(data)`;
   
         case 'javascript':
           return `const response = await fetch("${fullUrl}", {
     headers: ${JSON.stringify(headers, null, 2)}
   });
   const data = await response.json();
   console.log(data);`;
   
         case 'curl':
           const headerFlags = Object.entries(headers)
             .map(([key, value]) => `-H "${key}: ${value}"`)
             .join(' ');
           return `curl ${headerFlags} "${fullUrl}"`;
   
         default:
           return '';
       }
     };
     
     const code = generateCode(query, language);
     
     return (
       <Box sx={{ mt: 2 }}>
         <Typography variant="subtitle2" gutterBottom>
           {language.toUpperCase()} Code Example:
         </Typography>
         <Paper sx={{ p: 2, bgcolor: '#f5f5f5' }}>
           <pre style={{ margin: 0, fontSize: '14px' }}>
             <code>{code}</code>
           </pre>
           <Button
             size="small"
             onClick={() => navigator.clipboard.writeText(code)}
             sx={{ mt: 1 }}
           >
             Copy Code
           </Button>
         </Paper>
       </Box>
     );
   };
   ```

## Features and Functionality

### Core Features
1. **API Testing Interface**
   - Interactive query builder with parameter validation
   - Real-time API response viewing
   - Multiple response formats (JSON, table, charts)
   - Automatic code generation in multiple languages

2. **MCP Demonstration**
   - Natural language query interface
   - Conversation history and context
   - Example queries and suggestions
   - Integration with MCP server

3. **Data Visualization**
   - Player and team statistics charts
   - Shot chart visualizations
   - Historical trend analysis
   - Custom data filtering and grouping

4. **Documentation Integration**
   - Live examples with working code
   - Interactive API reference
   - Copy-paste code snippets
   - Usage analytics and insights

### Advanced Features
1. **Saved queries and collections**
   - User query history
   - Favorite API calls
   - Shareable query links
   - Export functionality

2. **Performance monitoring**
   - Response time tracking
   - Rate limit visualization
   - Error rate monitoring
   - Usage analytics

## Success Criteria
- Intuitive interface with <5 minute learning curve
- All API endpoints testable through the interface
- MCP natural language queries working accurately
- Code generation for 3+ programming languages
- Mobile-responsive design
- <2 second page load times

## Timeline
- **Week 1**: Frontend framework setup and basic API explorer
- **Week 2**: MCP demo interface and natural language queries
- **Week 3**: Data visualization components and charts
- **Week 4**: Code generation, documentation integration, and deployment

## Dependencies
- Completed REST API (Plan 13) and MCP server (Plan 14)
- API documentation (Plan 15)
- Frontend hosting platform (Vercel, Netlify, or similar)
- Domain and SSL certificate

## Next Steps
After completion:
1. User feedback collection and iteration
2. Advanced visualization features
3. Mobile app development consideration
4. Integration with developer onboarding flow