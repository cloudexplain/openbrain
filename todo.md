- check: https://github.com/NanoNets/docstrange
this works:
- More projects to check:
    - [ ] quivr (RAG), can be used by this project potentially
    - [ ] onyx
    - [ ] ragflow

- start backend using: cd backend && python run.py
- start db using: cd database && docker compose up
- then do:
curl --header "Content-Type: application/json"   --request POST   --data '{"message":"xyz","chat_id":"a2dcb1d9-3750-4655-a30a-06ed75bf9e73"}'  http://0.0.0.0:8000/api/v1/chat

curl --header "Content-Type: application/json"   --request GET http://0.0.0.0:8000/api/v1/chats


Plan:
- [x] Currently we get an error (see in the chats in the db) from the openai API
- [x] check whether we can call that locally
- [x] figure out what went wrong with that in the backend -> fix
- [x] commit
- [x] create one docker compose command to start all these things (using mounts so that local changes are reflected)
- [x] Sync to frontend!
- [x] Show old converations
- [x] Render markdown
- [x] Possibility to delete old conversations:
    - [x] check if this deletes in db as well? -> probably, just check in frontend!
- [x] add RAG
    Error: 2025-08-07 10:33:41,841 INFO sqlalchemy.engine.Engine INSERT INTO chat_knowledge (id, chat_id, content, chunk_index, message_ids, summary, token_count, embedding, chunk_metadata) VALUES ($1::UUID, $2::UUID, $3::VARCHAR, $4::INTEGER, $5::UUID[], $6::VARCHAR, $7::INTEGER, $8, $9::VARCHAR), ($10::UUID, $11 ... 386 characters truncated ... 42::VARCHAR, $43::INTEGER, $44, $45::VARCHAR) RETURNING chat_knowledge.created_at, chat_knowledge.id
- [ ] View in Knowledgebase not yet scrollable
2025-08-07 10:33:41,841 INFO sqlalchemy.engine.Engine [generated in 0.00585s (insertmanyvalues) 1/1 (ordered)] (UUID('52356c86-a835-4237-a3cc-6239daa313f3'), UUID('33062538-dcf1-4d4d-8667-245fc4790c07'), "USER:\nHi, is this working?\n\nASSISTANT:\nHello! Yes, I'm here and working. How can I assist you today?\n\nUSER:\nPerfect, that sounds great. Pls ex ... (698 characters truncated) ...  (arrows)** indicate causal influence from one variable to another.\n- **Acyclic** means the graph has no loops, ensuring that cause precedes effect.", 0, [UUID('25d518ab-7847-450a-ba8e-e69d10c6657d'), UUID('47e1c1e4-fa86-483b-bdb2-01c0693f66a1'), UUID('659642c4-5d12-4f76-9a1f-d9e72e3f9080'), UUID('d7def9ed-3576-4d1e-af68-1170371089e4')], None, 217, '[-0.019410191103816032,-0.017851708456873894,-0.04222070798277855,0.019424360245466232,0.029894528910517693,-0.02088366635143757,-0.01235451642423868 ... (32356 characters truncated) ... 0.04386420175433159,0.002392624970525503,0.016009865328669548,-0.012134911492466927,-0.019226007163524628,0.031594693660736084,0.0001595009525772184]', '{"chunk_index": 0, "chat_title": "Hi, is this working?", "message_count": 4, "chunk_start": 2, "chunk_end": 981, "created_at": "2025-08-06T15:00:36.046691+00:00"}', UUID('fdac46ea-a6be-45d1-a460-22b3c429b080'), UUID('33062538-dcf1-4d4d-8667-245fc4790c07'), 'This visual representation helps in understanding and communicating the structure of causal relationships among variables.\n\n### 2. **The Three Leve ... (542 characters truncated) ...  is where the concept of the **do-operator** (do(X)) comes into play, representing an external intervention that sets variable X to a specific value.', 1, [UUID('d7def9ed-3576-4d1e-af68-1170371089e4')], None, 152, '[-0.029359305277466774,0.004326079040765762,0.004329376388341188,0.025666309520602226,0.014679652638733387,0.00030829908791929483,0.00293296296149492 ... (32376 characters truncated) ... .04310251772403717,0.0015340764075517654,0.0002489473845344037,0.021432556211948395,-0.008276264183223248,-0.017950590699911118,0.008025667630136013]', '{"chunk_index": 1, "chat_title": "Hi, is this working?", "message_count": 1, "chunk_start": 983, "chunk_end": 1816, "created_at": "2025-08-06T15:00:36.046691+00:00"}', UUID('d710099c-2601-43cc-ab0c-e68180c72584'), UUID('33062538-dcf1-4d4d-8667-245fc4790c07'), '3. **Counterfactuals (Imagining):** The most abstract level, involving reasoning about hypothetical scenarios and outcomes that did not actually occu ... (660 characters truncated) ...  contributions is demonstrating that causal relationships can be inferred from observational data—not just from randomized experiments—provided that:', 2, [UUID('d7def9ed-3576-4d1e-af68-1170371089e4')], None, 190, '[0.0014885180862620473,-0.025695424526929855,0.0029857358895242214,0.052921995520591736,0.01592392474412918,-0.01005684956908226,-0.00505974376574158 ... (32373 characters truncated) ... 1,0.0640854462981224,0.011295686475932598,0.0067753237672150135,-0.007356463465839624,-0.03282221406698227,0.00911032222211361,-0.003234547097235918]', '{"chunk_index": 2, "chat_title": "Hi, is this working?", "message_count": 1, "chunk_start": 1818, "chunk_end": 2766, "created_at": "2025-08-06T15:00:36.046691+00:00"}', UUID('b40ff528-78f9-4210-8412-e3f405465d02'), UUID('33062538-dcf1-4d4d-8667-245fc4790c07'), "- The causal structure is correctly specified in the DAG.\n- Sufficient variables are measured to control for confounding influences.\n\n### 5. **App ... (541 characters truncated) ...  His work emphasizes that causation is not merely about association but involves understanding the underlying mechanisms and potential interventions.", 3, [UUID('d7def9ed-3576-4d1e-af68-1170371089e4')], None, 147, '[0.009098464623093605,-0.027382997795939445,-0.019786344841122627,0.07333838194608688,0.03747015446424484,-0.004564876202493906,-0.004201938863843679 ... (32402 characters truncated) ... 7,0.03469180688261986,0.007978364825248718,0.004095560405403376,0.013516288250684738,-0.01712063141167164,0.006464039441198111,-0.005456575658172369]', '{"chunk_index": 3, "chat_title": "Hi, is this working?", "message_count": 1, "chunk_start": 2768, "chunk_end": 3596, "created_at": "2025-08-06T15:00:36.046691+00:00"}', UUID('ed78c6ea-a6b7-4397-b5ed-29b5cdfbd282'), UUID('33062538-dcf1-4d4d-8667-245fc4790c07'), "### **Conclusion**\nJudea Pearl's contributions have provided a robust, mathematically grounded framework for causal reasoning. By integrating graphi ... (246 characters truncated) ... plines.\n\nUSER:\nCool, is this working as expected?\n\nASSISTANT:\nHello! Yes, everything seems to be working correctly. How can I assist you today?", 4, [UUID('d7def9ed-3576-4d1e-af68-1170371089e4'), UUID('39ce27af-8918-4402-b619-a2d86a82312c'), UUID('a60eb8e3-8418-4d36-95ed-7714e1c8e2a6')], None, 95, '[-0.013605291023850441,-0.02123216725885868,-0.03856664150953293,0.03065403178334236,0.009839475154876709,-0.012616215273737907,-0.012081380933523178 ... (32337 characters truncated) ... 038244277238845825,-0.01655786670744419,-0.00016564734687563032,-0.001785831875167787,-0.03742370754480362,0.021715715527534485,0.004253027029335499]', '{"chunk_index": 4, "chat_title": "Hi, is this working?", "message_count": 3, "chunk_start": 3598, "chunk_end": 4135, "created_at": "2025-08-06T15:00:36.046691+00:00"}')
2025-08-07 10:33:41,842 INFO sqlalchemy.engine.Engine ROLLBACK
ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "chat_knowledge" does not exist\n[SQL: INSERT IN…


Debugging:
psql -h localhost -U secondbrain
then enter password: secondbrain_password

Latest todo, 13.09.2025:
- check backend/try_calling_think.py and the backend/try_calling_think_anthropic.py, the problem seems to be that openai models do not like to call tools as their anthropic counterparts
- idea: try to rewrite the prompt, azure openai models just don't seem to like to call the think_tool, when we basically renamed it to save things and do a bit more, it was called. So we should experiment with different prompts to see if these things get better.
