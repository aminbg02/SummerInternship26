--
-- PostgreSQL database dump
--

\restrict DqhaZ6axAYYDMOIeZrjRZXhLNc3jkk48MG6N6PW2yUJDaytB97lCLfor0M0i8qs

-- Dumped from database version 16.14 (Debian 16.14-1.pgdg13+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: companies; Type: TABLE; Schema: public; Owner: orange
--

CREATE TABLE public.companies (
    id integer NOT NULL,
    name character varying(200) NOT NULL,
    domain character varying(255),
    daily_token_limit integer,
    daily_request_limit integer,
    created_at timestamp without time zone NOT NULL,
    qdrant_collection character varying(255),
    qdrant_url character varying(255),
    embedding_model character varying(255)
);


ALTER TABLE public.companies OWNER TO orange;

--
-- Name: companies_id_seq; Type: SEQUENCE; Schema: public; Owner: orange
--

CREATE SEQUENCE public.companies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.companies_id_seq OWNER TO orange;

--
-- Name: companies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: orange
--

ALTER SEQUENCE public.companies_id_seq OWNED BY public.companies.id;


--
-- Name: conversations; Type: TABLE; Schema: public; Owner: orange
--

CREATE TABLE public.conversations (
    id integer NOT NULL,
    company_id integer NOT NULL,
    user_id integer NOT NULL,
    title character varying(300),
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.conversations OWNER TO orange;

--
-- Name: conversations_id_seq; Type: SEQUENCE; Schema: public; Owner: orange
--

CREATE SEQUENCE public.conversations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.conversations_id_seq OWNER TO orange;

--
-- Name: conversations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: orange
--

ALTER SEQUENCE public.conversations_id_seq OWNED BY public.conversations.id;


--
-- Name: documents; Type: TABLE; Schema: public; Owner: orange
--

CREATE TABLE public.documents (
    id integer NOT NULL,
    company_id integer NOT NULL,
    filename character varying(300) NOT NULL,
    status character varying(30) NOT NULL,
    scope character varying(20) NOT NULL,
    created_by integer,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.documents OWNER TO orange;

--
-- Name: documents_id_seq; Type: SEQUENCE; Schema: public; Owner: orange
--

CREATE SEQUENCE public.documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.documents_id_seq OWNER TO orange;

--
-- Name: documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: orange
--

ALTER SEQUENCE public.documents_id_seq OWNED BY public.documents.id;


--
-- Name: kb_deletions; Type: TABLE; Schema: public; Owner: orange
--

CREATE TABLE public.kb_deletions (
    id integer NOT NULL,
    company_id integer NOT NULL,
    document_id integer,
    user_id integer,
    filename character varying(300) NOT NULL,
    chunks_deleted integer NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.kb_deletions OWNER TO orange;

--
-- Name: kb_deletions_id_seq; Type: SEQUENCE; Schema: public; Owner: orange
--

CREATE SEQUENCE public.kb_deletions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.kb_deletions_id_seq OWNER TO orange;

--
-- Name: kb_deletions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: orange
--

ALTER SEQUENCE public.kb_deletions_id_seq OWNED BY public.kb_deletions.id;


--
-- Name: kb_ingestions; Type: TABLE; Schema: public; Owner: orange
--

CREATE TABLE public.kb_ingestions (
    id integer NOT NULL,
    company_id integer NOT NULL,
    document_id integer,
    user_id integer,
    filename character varying(300) NOT NULL,
    chunks_indexed integer NOT NULL,
    chunks_blocked integer NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.kb_ingestions OWNER TO orange;

--
-- Name: kb_ingestions_id_seq; Type: SEQUENCE; Schema: public; Owner: orange
--

CREATE SEQUENCE public.kb_ingestions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.kb_ingestions_id_seq OWNER TO orange;

--
-- Name: kb_ingestions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: orange
--

ALTER SEQUENCE public.kb_ingestions_id_seq OWNED BY public.kb_ingestions.id;


--
-- Name: llm_providers; Type: TABLE; Schema: public; Owner: orange
--

CREATE TABLE public.llm_providers (
    id integer NOT NULL,
    display_name character varying(120) NOT NULL,
    provider_key character varying(50) NOT NULL,
    base_url character varying(300),
    api_key_encrypted text,
    model_name character varying(150) NOT NULL,
    enabled boolean NOT NULL,
    is_free boolean NOT NULL,
    rate_limit_rpm integer,
    rate_limit_rpd integer,
    priority integer NOT NULL,
    default_temperature double precision,
    max_output_tokens integer,
    company_id integer,
    created_by integer,
    created_at timestamp without time zone NOT NULL,
    unavailable_until timestamp without time zone,
    last_error character varying(200),
    rate_limit_group character varying(60)
);


ALTER TABLE public.llm_providers OWNER TO orange;

--
-- Name: llm_providers_id_seq; Type: SEQUENCE; Schema: public; Owner: orange
--

CREATE SEQUENCE public.llm_providers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.llm_providers_id_seq OWNER TO orange;

--
-- Name: llm_providers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: orange
--

ALTER SEQUENCE public.llm_providers_id_seq OWNED BY public.llm_providers.id;


--
-- Name: messages; Type: TABLE; Schema: public; Owner: orange
--

CREATE TABLE public.messages (
    id integer NOT NULL,
    conversation_id integer NOT NULL,
    role character varying(20) NOT NULL,
    content text NOT NULL,
    created_at timestamp without time zone NOT NULL,
    sources json,
    feedback character varying(10),
    provider_id integer
);


ALTER TABLE public.messages OWNER TO orange;

--
-- Name: messages_id_seq; Type: SEQUENCE; Schema: public; Owner: orange
--

CREATE SEQUENCE public.messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.messages_id_seq OWNER TO orange;

--
-- Name: messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: orange
--

ALTER SEQUENCE public.messages_id_seq OWNED BY public.messages.id;


--
-- Name: pii_rules; Type: TABLE; Schema: public; Owner: orange
--

CREATE TABLE public.pii_rules (
    id integer NOT NULL,
    entity_name character varying(50) NOT NULL,
    pattern character varying(300) NOT NULL,
    score double precision NOT NULL,
    enabled boolean NOT NULL,
    created_by integer,
    created_at timestamp without time zone,
    company_id integer
);


ALTER TABLE public.pii_rules OWNER TO orange;

--
-- Name: pii_rules_id_seq; Type: SEQUENCE; Schema: public; Owner: orange
--

CREATE SEQUENCE public.pii_rules_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pii_rules_id_seq OWNER TO orange;

--
-- Name: pii_rules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: orange
--

ALTER SEQUENCE public.pii_rules_id_seq OWNED BY public.pii_rules.id;


--
-- Name: provider_call_log; Type: TABLE; Schema: public; Owner: orange
--

CREATE TABLE public.provider_call_log (
    id integer NOT NULL,
    provider_id integer NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.provider_call_log OWNER TO orange;

--
-- Name: provider_call_log_id_seq; Type: SEQUENCE; Schema: public; Owner: orange
--

CREATE SEQUENCE public.provider_call_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.provider_call_log_id_seq OWNER TO orange;

--
-- Name: provider_call_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: orange
--

ALTER SEQUENCE public.provider_call_log_id_seq OWNED BY public.provider_call_log.id;


--
-- Name: staged_chunks; Type: TABLE; Schema: public; Owner: orange
--

CREATE TABLE public.staged_chunks (
    id integer NOT NULL,
    company_id integer NOT NULL,
    conversation_id integer,
    document_id integer,
    text text NOT NULL,
    category character varying(40),
    created_at timestamp without time zone NOT NULL,
    expires_at timestamp without time zone
);


ALTER TABLE public.staged_chunks OWNER TO orange;

--
-- Name: staged_chunks_id_seq; Type: SEQUENCE; Schema: public; Owner: orange
--

CREATE SEQUENCE public.staged_chunks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.staged_chunks_id_seq OWNER TO orange;

--
-- Name: staged_chunks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: orange
--

ALTER SEQUENCE public.staged_chunks_id_seq OWNED BY public.staged_chunks.id;


--
-- Name: token_requests; Type: TABLE; Schema: public; Owner: orange
--

CREATE TABLE public.token_requests (
    id integer NOT NULL,
    requester_id integer NOT NULL,
    company_id integer NOT NULL,
    scope character varying(10) NOT NULL,
    requested_limit integer NOT NULL,
    reason text NOT NULL,
    status character varying(10) NOT NULL,
    decision_reason text,
    reviewed_by integer,
    reviewed_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.token_requests OWNER TO orange;

--
-- Name: token_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: orange
--

CREATE SEQUENCE public.token_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.token_requests_id_seq OWNER TO orange;

--
-- Name: token_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: orange
--

ALTER SEQUENCE public.token_requests_id_seq OWNED BY public.token_requests.id;


--
-- Name: token_usage; Type: TABLE; Schema: public; Owner: orange
--

CREATE TABLE public.token_usage (
    id integer NOT NULL,
    company_id integer NOT NULL,
    user_id integer,
    provider_id integer,
    conversation_id integer,
    prompt_tokens integer NOT NULL,
    completion_tokens integer NOT NULL,
    total_tokens integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    reasoning_tokens integer
);


ALTER TABLE public.token_usage OWNER TO orange;

--
-- Name: token_usage_id_seq; Type: SEQUENCE; Schema: public; Owner: orange
--

CREATE SEQUENCE public.token_usage_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.token_usage_id_seq OWNER TO orange;

--
-- Name: token_usage_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: orange
--

ALTER SEQUENCE public.token_usage_id_seq OWNED BY public.token_usage.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: orange
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(20) NOT NULL,
    company_id integer,
    daily_token_limit integer,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.users OWNER TO orange;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: orange
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO orange;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: orange
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: companies id; Type: DEFAULT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.companies ALTER COLUMN id SET DEFAULT nextval('public.companies_id_seq'::regclass);


--
-- Name: conversations id; Type: DEFAULT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.conversations ALTER COLUMN id SET DEFAULT nextval('public.conversations_id_seq'::regclass);


--
-- Name: documents id; Type: DEFAULT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.documents ALTER COLUMN id SET DEFAULT nextval('public.documents_id_seq'::regclass);


--
-- Name: kb_deletions id; Type: DEFAULT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.kb_deletions ALTER COLUMN id SET DEFAULT nextval('public.kb_deletions_id_seq'::regclass);


--
-- Name: kb_ingestions id; Type: DEFAULT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.kb_ingestions ALTER COLUMN id SET DEFAULT nextval('public.kb_ingestions_id_seq'::regclass);


--
-- Name: llm_providers id; Type: DEFAULT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.llm_providers ALTER COLUMN id SET DEFAULT nextval('public.llm_providers_id_seq'::regclass);


--
-- Name: messages id; Type: DEFAULT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.messages ALTER COLUMN id SET DEFAULT nextval('public.messages_id_seq'::regclass);


--
-- Name: pii_rules id; Type: DEFAULT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.pii_rules ALTER COLUMN id SET DEFAULT nextval('public.pii_rules_id_seq'::regclass);


--
-- Name: provider_call_log id; Type: DEFAULT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.provider_call_log ALTER COLUMN id SET DEFAULT nextval('public.provider_call_log_id_seq'::regclass);


--
-- Name: staged_chunks id; Type: DEFAULT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.staged_chunks ALTER COLUMN id SET DEFAULT nextval('public.staged_chunks_id_seq'::regclass);


--
-- Name: token_requests id; Type: DEFAULT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.token_requests ALTER COLUMN id SET DEFAULT nextval('public.token_requests_id_seq'::regclass);


--
-- Name: token_usage id; Type: DEFAULT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.token_usage ALTER COLUMN id SET DEFAULT nextval('public.token_usage_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: companies; Type: TABLE DATA; Schema: public; Owner: orange
--

COPY public.companies (id, name, domain, daily_token_limit, daily_request_limit, created_at, qdrant_collection, qdrant_url, embedding_model) FROM stdin;
6	utm	utm.com	5000	\N	2026-07-14 09:08:57.031377	kb_6_utm	\N	\N
9	TEST	test.com	400	\N	2026-07-22 19:43:38.811197	kb_9_test	http://localhost:6343	\N
10	Oxford	oxford.us	4000	\N	2026-07-25 19:27:19.415822	kb_10_oxford	http://localhost:6353	BAAI/bge-small-en-v1.5
8	globalnet	globalnet.com	4000	\N	2026-07-14 12:52:34.323331	kb_8_globalnet	\N	BAAI/bge-small-en-v1.5
1	Telecom	telecom.com	200000	\N	2026-07-08 11:28:06.062523	kb_1_telecom	\N	\N
2	Ooredoo	ooredoo.tn	120000	\N	2026-07-08 11:28:06.065273	kb_2_ooredoo	\N	\N
3	BIAT	biat.com.tn	60000	\N	2026-07-08 11:28:06.067755	kb_3_biat	\N	\N
4	Topnet	topnet.com	25000	\N	2026-07-08 11:28:06.069861	kb_4_topnet	\N	\N
5	FIAT	fiat.com	10000	\N	2026-07-13 19:25:33.668165	kb_5_fiat	\N	\N
\.


--
-- Data for Name: conversations; Type: TABLE DATA; Schema: public; Owner: orange
--

COPY public.conversations (id, company_id, user_id, title, created_at) FROM stdin;
3	1	3	\N	2026-07-13 10:12:48.803522
5	1	3	\N	2026-07-13 10:13:11.705687
7	1	3	\N	2026-07-13 10:13:17.86261
13	3	1	\N	2026-07-13 10:21:36.970761
14	3	1	\N	2026-07-13 10:23:32.263353
1	1	3	How much does the Fiber Pro plan cost and what internet speed does it include?	2026-07-08 22:20:56.063648
2	1	3	How much does the Ooredoo Hayya prepaid plan cost?	2026-07-08 22:21:26.455897
4	1	3	What is the refund policy?	2026-07-13 10:13:07.912093
6	1	3	What is the refund policy?	2026-07-13 10:13:14.676926
8	3	1	What is the refund policy?	2026-07-13 10:20:14.048671
9	2	1	What is the refund policy?	2026-07-13 10:20:14.761796
10	1	1	What is the refund policy?	2026-07-13 10:20:15.583276
11	4	1	What is the refund policy?	2026-07-13 10:20:16.534071
64	3	9	\N	2026-07-14 10:30:32.405657
15	3	1	good morning	2026-07-13 10:23:38.219346
17	1	1	What is the refund policy?	2026-07-13 10:36:34.374975
18	2	1	What is the refund policy?	2026-07-13 10:36:37.052135
65	3	1	good morning	2026-07-16 09:03:43.595037
20	3	1	\N	2026-07-13 10:41:48.225072
12	1	3	Refund policy — Q3 escalation	2026-07-13 10:20:17.642447
21	3	1	\N	2026-07-13 13:25:19.999236
22	3	1	\N	2026-07-13 13:30:46.316135
23	3	1	\N	2026-07-13 13:30:58.060987
24	1	3	What is the refund policy?	2026-07-13 13:35:00.59897
26	3	1	\N	2026-07-13 13:35:17.466029
25	1	3	What is the refund policy?	2026-07-13 13:35:14.642688
27	3	1	good mrning	2026-07-13 13:35:47.866993
30	3	1	\N	2026-07-13 13:45:17.425372
28	3	1	good morning	2026-07-13 13:44:26.285618
31	1	3	What is the refund policy?	2026-07-13 13:46:24.760082
32	1	3	What is the refund policy?	2026-07-13 13:52:13.137932
33	3	1	\N	2026-07-13 14:02:57.631638
34	3	1	hey	2026-07-13 14:07:00.593875
35	1	4	What is the refund policy?	2026-07-13 14:12:40.607377
36	1	4	What compensation do I get if there is an outage?	2026-07-13 14:12:50.192718
37	1	4	How long is prepaid credit valid for?	2026-07-13 14:14:39.599449
38	1	4	How do I raise a complaint and how fast will you respond?	2026-07-13 14:14:45.881
39	1	4	How much data does the Unlimited mobile plan include and what does it cost?	2026-07-13 14:16:35.35069
40	2	6	What is the wallet limit for mobile money?	2026-07-13 14:16:38.649591
41	1	4	What is the refund policy?	2026-07-13 14:26:03.789885
42	1	4	What compensation do I get if there is an outage?	2026-07-13 14:26:17.324267
43	2	7	How does the family plan discount work?	2026-07-13 14:28:58.591146
44	2	6	What does Device Care cover and how much is it?	2026-07-13 14:29:04.822226
45	1	4	How long is prepaid credit valid for?	2026-07-13 14:29:19.761808
46	2	6	What is the wallet limit for mobile money?	2026-07-13 14:29:27.500693
47	2	7	I am a student. What offers do you have?	2026-07-13 14:31:14.282223
48	2	6	How many times can I transfer my eSIM to a new device?	2026-07-13 14:31:20.423494
49	2	7	What are your call centre hours and what number do I call?	2026-07-13 14:33:33.585588
50	2	6	Can I get a free signal booster if my indoor signal is weak?	2026-07-13 14:33:36.794293
51	3	9	How much can I borrow for a mortgage and over how long?	2026-07-13 14:33:39.938234
52	3	1	\N	2026-07-13 19:29:01.21388
53	1	13	what is the cost of a monthly plan	2026-07-13 19:39:52.394656
54	3	1	\N	2026-07-13 19:43:47.129079
55	3	10	can you tell me the working hours of biat	2026-07-13 19:47:12.369879
56	3	10	good evening	2026-07-13 19:47:54.381737
57	1	13	read this	2026-07-13 19:55:35.023509
58	1	13	hey if i give you a file can you read it	2026-07-13 19:58:52.323596
59	1	13	who is the client mentioned here	2026-07-13 19:59:45.449645
62	3	9	good morning	2026-07-14 10:05:05.992132
63	3	9	good morning	2026-07-14 10:05:26.151506
66	3	1	good morning	2026-07-16 09:05:19.090837
67	3	1	good morning	2026-07-16 09:08:39.680582
68	4	16	Is there a data cap on the unlimited plan?	2026-07-12 15:26:21
69	2	7	What is the wallet limit for mobile money?	2026-07-12 13:08:06
70	1	3	How much does the Fiber Pro plan cost?	2026-07-12 08:41:40
71	4	16	What TV bundles do you offer?	2026-07-14 14:35:08
72	2	14	How does the family plan discount work?	2026-07-14 09:24:58
73	3	10	What documents do I need to open a business account?	2026-07-14 16:15:28
74	3	10	What interest does the savings account pay?	2026-07-14 10:20:40
75	3	15	What are the fees for an international transfer?	2026-07-14 12:13:30
76	1	3	What compensation do I get if there is an outage?	2026-07-14 09:18:54
77	1	4	How do loyalty points work?	2026-07-15 14:47:13
78	1	4	What is your refund policy?	2026-07-15 11:29:01
79	2	14	What does Device Care cover?	2026-07-15 11:12:40
80	4	12	How much is a static IP address?	2026-07-15 16:57:03
81	4	16	Is there a data cap on the unlimited plan?	2026-07-15 16:23:24
82	2	7	What is the wallet limit for mobile money?	2026-07-15 09:34:41
83	2	1	What prepaid mobile plans do you have and how much data do they include?	2026-07-16 09:40:29.187518
84	3	1	\N	2026-07-20 08:57:30.791892
85	3	1	goodm orni	2026-07-20 08:57:51.178568
86	3	1	good morning	2026-07-20 08:58:18.8765
87	1	3	Cuanto cuesta el plan Business Fiber y que garantia de tiempo de actividad tiene	2026-07-23 21:15:47.115003
88	1	3	\N	2026-07-23 21:16:02.060369
89	1	3	\N	2026-07-23 21:16:15.119221
90	1	3	Quels sont les forfaits mobiles disponibles et combien coute le forfait illimite	2026-07-23 21:16:29.226201
91	1	3	Jakie sa plany biznesowe i ile kosztuje Business Fiber?	2026-07-23 21:16:44.629749
92	4	16	Is there a data cap on the unlimited plan?	2026-07-24 15:26:21
93	2	7	What is the wallet limit for mobile money?	2026-07-24 17:18:45
94	1	3	How much does the Fiber Pro plan cost?	2026-07-24 14:35:08
95	4	16	What TV bundles do you offer?	2026-07-24 16:15:28
96	2	14	How does the family plan discount work?	2026-07-24 14:40:42
97	3	10	What documents do I need to open a business account?	2026-07-24 11:30:49
98	3	10	What interest does the savings account pay?	2026-07-24 13:35:04
99	3	15	What are the fees for an international transfer?	2026-07-25 14:51:16
100	1	3	What compensation do I get if there is an outage?	2026-07-25 15:10:12
101	1	4	How do loyalty points work?	2026-07-25 09:13:45
102	3	1	bonjour	2026-07-25 19:48:49.002691
103	3	9	What is the daily ATM withdrawal limit on a Visa Classic card?	2026-07-25 19:59:15.535325
104	1	3	What are your support hours?	2026-07-31 21:28:09.605785
106	4	12	What is your refund policy?	2026-07-31 21:29:02.943752
107	1	13	What mobile plans does Telecom offer?	2026-08-02 19:56:46.705789
118	2	1	ping	2026-08-02 19:57:43.16985
119	3	1	ping	2026-08-02 19:57:44.318211
120	4	1	ping	2026-08-02 19:57:44.931201
121	5	1	ping	2026-08-02 19:57:45.555219
122	6	1	ping	2026-08-02 19:57:46.152455
123	2	1	\N	2026-08-02 19:57:54.328088
124	2	1	What are your customer support hours?	2026-08-02 19:57:55.014942
125	2	1	\N	2026-08-02 19:57:56.2816
126	2	1	What internet plans do you offer?	2026-08-02 19:57:57.294314
128	1	1	What happens if I cancel my contract early?	2026-08-02 20:03:44.731264
129	1	1	Do you offer any discounts for customers with disabilities?	2026-08-02 20:03:45.740195
130	1	1	\N	2026-08-02 20:03:46.598695
131	1	1	\N	2026-08-02 20:03:47.662899
132	1	1	\N	2026-08-02 20:04:03.33134
133	1	1	How does the SLA credit work for Business Fiber?	2026-08-02 20:04:19.378762
134	1	1	What is the process for upgrading my mobile plan in the app?	2026-08-02 20:04:20.232523
135	1	1	What home internet options are available?	2026-08-02 20:04:20.936503
136	1	1	How does the SLA credit work for Business Fiber?	2026-08-02 22:58:49.937991
137	1	1	How does the SLA credit work for Business Fiber?	2026-08-02 22:59:54.733352
138	1	1	What mobile plans does Telecom offer?	2026-08-02 22:59:59.95182
139	1	1	What happens if I cancel my contract early?	2026-08-02 23:00:00.79369
140	1	1	What home internet options are available?	2026-08-02 23:00:01.817845
141	1	1	Do you offer any discounts for customers with disabilities?	2026-08-02 23:00:02.904477
146	3	1	ping	2026-08-02 23:03:15.721887
147	4	1	ping	2026-08-02 23:03:20.963477
148	5	1	ping	2026-08-02 23:03:21.477137
149	6	1	ping	2026-08-02 23:03:22.03003
150	3	1	How do I reset my password?	2026-08-02 23:03:43.664493
151	3	1	How do I reset my password?	2026-08-02 23:04:45.625283
152	3	1	Do you offer student discounts?	2026-08-02 23:04:50.392427
153	3	1	What is your loyalty rewards program?	2026-08-02 23:04:50.96891
154	3	1	good morning what is your wourking hours	2026-08-03 09:10:59.691736
\.


--
-- Data for Name: documents; Type: TABLE DATA; Schema: public; Owner: orange
--

COPY public.documents (id, company_id, filename, status, scope, created_by, created_at) FROM stdin;
1	1	telecom_plans.txt	ingested	kb	\N	2026-07-08 11:28:09.592131
2	1	telecom_billing.txt	ingested	kb	\N	2026-07-08 11:28:10.395775
3	1	telecom_support.txt	ingested	kb	\N	2026-07-08 11:28:10.449386
4	1	telecom_roaming.txt	ingested	kb	\N	2026-07-08 11:28:10.511283
5	2	ooredoo_plans.txt	ingested	kb	\N	2026-07-08 11:28:10.566955
6	2	ooredoo_support.txt	ingested	kb	\N	2026-07-08 11:28:10.781883
7	3	biat_accounts.txt	ingested	kb	\N	2026-07-08 11:28:10.834642
8	3	biat_cards.txt	ingested	kb	\N	2026-07-08 11:28:11.07033
9	4	topnet_plans.txt	ingested	kb	\N	2026-07-08 11:28:11.123094
10	4	topnet_support.txt	ingested	kb	\N	2026-07-08 11:28:11.343371
11	1	telecom_contract_terms.pdf	ingested	kb	\N	2026-07-12 22:28:16.121661
12	1	telecom_devices.pdf	ingested	kb	\N	2026-07-12 22:28:17.220059
13	1	telecom_business.docx	ingested	kb	\N	2026-07-12 22:28:17.519245
14	1	telecom_privacy.docx	ingested	kb	\N	2026-07-12 22:28:17.693074
15	2	ooredoo_billing.txt	ingested	kb	\N	2026-07-12 22:28:17.862124
16	2	ooredoo_roaming.pdf	ingested	kb	\N	2026-07-12 22:28:18.001319
17	2	ooredoo_business.pdf	ingested	kb	\N	2026-07-12 22:28:18.204254
18	2	ooredoo_sim_esim.docx	ingested	kb	\N	2026-07-12 22:28:18.410734
19	3	biat_transfers.txt	ingested	kb	\N	2026-07-12 22:28:18.586307
20	3	biat_loans.pdf	ingested	kb	\N	2026-07-12 22:28:19.739031
21	3	biat_security.pdf	ingested	kb	\N	2026-07-12 22:28:20.649881
22	3	biat_net_banking.docx	ingested	kb	\N	2026-07-12 22:28:20.862958
23	3	biat_branches.docx	ingested	kb	\N	2026-07-12 22:28:21.12333
24	4	topnet_billing.txt	ingested	kb	\N	2026-07-12 22:28:21.393586
25	4	topnet_troubleshooting.pdf	ingested	kb	\N	2026-07-12 22:28:21.673754
26	4	topnet_business.pdf	ingested	kb	\N	2026-07-12 22:28:21.932777
27	4	topnet_installation.docx	ingested	kb	\N	2026-07-12 22:28:22.172687
28	1	telecom_coverage.txt	ingested	kb	\N	2026-07-13 14:10:44.780955
29	1	telecom_cancellation.txt	ingested	kb	\N	2026-07-13 14:10:45.361631
30	1	telecom_complaints.docx	ingested	kb	\N	2026-07-13 14:10:45.475417
31	1	telecom_app.txt	ingested	kb	\N	2026-07-13 14:10:45.564858
32	1	telecom_loyalty.pdf	ingested	kb	\N	2026-07-13 14:11:37.251695
33	1	telecom_prepaid.txt	ingested	kb	\N	2026-07-13 14:11:37.753238
34	1	telecom_accessibility.docx	ingested	kb	\N	2026-07-13 14:11:37.839594
35	2	ooredoo_coverage.txt	ingested	kb	\N	2026-07-13 14:11:37.971103
36	2	ooredoo_mobile_money.pdf	ingested	kb	\N	2026-07-13 14:11:38.025238
37	2	ooredoo_family.txt	ingested	kb	\N	2026-07-13 14:11:38.092897
38	2	ooredoo_device_care.docx	ingested	kb	\N	2026-07-13 14:11:38.219047
39	2	ooredoo_customer_care.txt	ingested	kb	\N	2026-07-13 14:11:38.278888
40	2	ooredoo_youth.txt	ingested	kb	\N	2026-07-13 14:11:38.321906
41	2	ooredoo_esim_transfer.docx	ingested	kb	\N	2026-07-13 14:11:38.398713
42	3	biat_mortgages.pdf	ingested	kb	\N	2026-07-13 14:11:38.561188
43	3	biat_fees.txt	ingested	kb	\N	2026-07-13 14:11:38.628209
44	3	biat_business_banking.docx	ingested	kb	\N	2026-07-13 14:11:38.731677
45	3	biat_kyc.txt	ingested	kb	\N	2026-07-13 14:11:38.797635
46	3	biat_travel_forex.pdf	ingested	kb	\N	2026-07-13 14:11:38.868466
47	3	biat_savings.txt	ingested	kb	\N	2026-07-13 14:11:38.908694
48	3	biat_complaints.docx	ingested	kb	\N	2026-07-13 14:11:38.98446
49	4	topnet_fair_use.txt	ingested	kb	\N	2026-07-13 14:11:39.108913
50	4	topnet_static_ip.txt	ingested	kb	\N	2026-07-13 14:11:39.161372
51	4	topnet_tv.docx	ingested	kb	\N	2026-07-13 14:11:39.268569
52	4	topnet_moving.txt	ingested	kb	\N	2026-07-13 14:11:39.338809
53	4	topnet_hosting.pdf	ingested	kb	\N	2026-07-13 14:11:39.402163
54	4	topnet_security.docx	ingested	kb	\N	2026-07-13 14:11:39.486703
55	4	topnet_speed.txt	ingested	kb	\N	2026-07-13 14:11:39.53718
56	1	03_prompt_injection.pdf	filtered	ephemeral	13	2026-07-13 19:55:30.947817
57	1	04_fully_poisoned.txt	rejected	ephemeral	13	2026-07-13 19:58:58.216194
58	1	05_ephemeral_attachment.docx	filtered	ephemeral	13	2026-07-13 19:59:28.848052
59	6	utm_programs.pdf	ingested	kb	\N	2026-07-14 09:32:10.49633
60	6	utm_admissions.txt	ingested	kb	\N	2026-07-14 09:32:47.934146
61	6	utm_fees_and_scholarships.docx	ingested	kb	\N	2026-07-14 09:32:48.038191
62	6	utm_library.txt	ingested	kb	\N	2026-07-14 09:32:48.143312
63	6	utm_it_support.pdf	ingested	kb	\N	2026-07-14 09:32:48.22637
64	6	utm_examinations.docx	ingested	kb	\N	2026-07-14 09:32:48.356672
65	5	fiat_warranty.pdf	ingested	kb	\N	2026-07-14 09:46:57.685018
66	5	fiat_servicing.txt	ingested	kb	\N	2026-07-14 09:46:58.219642
67	5	fiat_parts_and_repairs.docx	ingested	kb	\N	2026-07-14 09:46:58.418471
68	5	fiat_roadside_assistance.txt	ingested	kb	\N	2026-07-14 09:46:58.600382
69	5	fiat_purchase_and_financing.pdf	ingested	kb	\N	2026-07-14 09:46:58.72186
70	8	02_pii_redaction.txt	ingested	kb	24	2026-07-14 12:53:41.069004
71	8	globalnet_plans.txt	ingested	kb	\N	2026-07-25 19:44:21.52763
72	8	globalnet_billing.txt	ingested	kb	\N	2026-07-25 19:45:15.634441
73	8	globalnet_support.txt	ingested	kb	\N	2026-07-25 19:45:15.689555
74	8	globalnet_installation.pdf	ingested	kb	\N	2026-07-25 19:45:15.824254
75	8	globalnet_business.docx	ingested	kb	\N	2026-07-25 19:45:15.934115
\.


--
-- Data for Name: kb_deletions; Type: TABLE DATA; Schema: public; Owner: orange
--

COPY public.kb_deletions (id, company_id, document_id, user_id, filename, chunks_deleted, created_at) FROM stdin;
\.


--
-- Data for Name: kb_ingestions; Type: TABLE DATA; Schema: public; Owner: orange
--

COPY public.kb_ingestions (id, company_id, document_id, user_id, filename, chunks_indexed, chunks_blocked, created_at) FROM stdin;
1	1	1	1	telecom_plans.txt	1	0	2026-07-08 11:28:10.386246
2	1	2	1	telecom_billing.txt	1	0	2026-07-08 11:28:10.442362
3	1	3	1	telecom_support.txt	1	0	2026-07-08 11:28:10.503897
4	1	4	1	telecom_roaming.txt	1	0	2026-07-08 11:28:10.558665
5	2	5	1	ooredoo_plans.txt	1	0	2026-07-08 11:28:10.773024
6	2	6	1	ooredoo_support.txt	1	0	2026-07-08 11:28:10.82436
7	3	7	1	biat_accounts.txt	1	0	2026-07-08 11:28:11.061539
8	3	8	1	biat_cards.txt	1	0	2026-07-08 11:28:11.114503
9	4	9	1	topnet_plans.txt	1	0	2026-07-08 11:28:11.336141
10	4	10	1	topnet_support.txt	1	0	2026-07-08 11:28:11.376837
11	1	11	1	telecom_contract_terms.pdf	3	0	2026-07-12 22:28:17.182609
12	1	12	1	telecom_devices.pdf	3	0	2026-07-12 22:28:17.360374
13	1	13	1	telecom_business.docx	2	0	2026-07-12 22:28:17.628093
14	1	14	1	telecom_privacy.docx	3	0	2026-07-12 22:28:17.842465
15	2	15	1	ooredoo_billing.txt	2	0	2026-07-12 22:28:17.968433
16	2	16	1	ooredoo_roaming.pdf	3	0	2026-07-12 22:28:18.156776
17	2	17	1	ooredoo_business.pdf	2	0	2026-07-12 22:28:18.350292
18	2	18	1	ooredoo_sim_esim.docx	3	0	2026-07-12 22:28:18.568263
19	3	19	1	biat_transfers.txt	2	0	2026-07-12 22:28:19.703891
20	3	20	1	biat_loans.pdf	3	0	2026-07-12 22:28:20.619043
21	3	21	1	biat_security.pdf	3	0	2026-07-12 22:28:20.80247
22	3	22	1	biat_net_banking.docx	3	0	2026-07-12 22:28:21.032009
23	3	23	1	biat_branches.docx	3	0	2026-07-12 22:28:21.373175
24	4	24	1	topnet_billing.txt	2	0	2026-07-12 22:28:21.628701
25	4	25	1	topnet_troubleshooting.pdf	3	0	2026-07-12 22:28:21.896413
26	4	26	1	topnet_business.pdf	3	0	2026-07-12 22:28:22.117068
27	4	27	1	topnet_installation.docx	3	0	2026-07-12 22:28:22.318446
28	1	28	1	telecom_coverage.txt	1	0	2026-07-13 14:10:45.347372
29	1	29	1	telecom_cancellation.txt	1	0	2026-07-13 14:10:45.434709
30	1	30	1	telecom_complaints.docx	1	0	2026-07-13 14:10:45.557
31	1	31	1	telecom_app.txt	1	0	2026-07-13 14:10:45.608489
32	1	32	1	telecom_loyalty.pdf	1	0	2026-07-13 14:11:37.742919
33	1	33	1	telecom_prepaid.txt	1	0	2026-07-13 14:11:37.792661
34	1	34	1	telecom_accessibility.docx	1	0	2026-07-13 14:11:37.900625
35	2	35	1	ooredoo_coverage.txt	1	0	2026-07-13 14:11:38.012999
36	2	36	1	ooredoo_mobile_money.pdf	1	0	2026-07-13 14:11:38.085768
37	2	37	1	ooredoo_family.txt	1	0	2026-07-13 14:11:38.164507
38	2	38	1	ooredoo_device_care.docx	1	0	2026-07-13 14:11:38.273099
39	2	39	1	ooredoo_customer_care.txt	1	0	2026-07-13 14:11:38.313616
40	2	40	1	ooredoo_youth.txt	1	0	2026-07-13 14:11:38.361012
41	2	41	1	ooredoo_esim_transfer.docx	1	0	2026-07-13 14:11:38.46066
42	3	42	1	biat_mortgages.pdf	1	0	2026-07-13 14:11:38.623231
43	3	43	1	biat_fees.txt	1	0	2026-07-13 14:11:38.684636
44	3	44	1	biat_business_banking.docx	1	0	2026-07-13 14:11:38.789032
45	3	45	1	biat_kyc.txt	1	0	2026-07-13 14:11:38.85186
46	3	46	1	biat_travel_forex.pdf	1	0	2026-07-13 14:11:38.901672
47	3	47	1	biat_savings.txt	1	0	2026-07-13 14:11:38.948084
48	3	48	1	biat_complaints.docx	1	0	2026-07-13 14:11:39.03833
49	4	49	1	topnet_fair_use.txt	1	0	2026-07-13 14:11:39.150845
50	4	50	1	topnet_static_ip.txt	1	0	2026-07-13 14:11:39.218156
51	4	51	1	topnet_tv.docx	1	0	2026-07-13 14:11:39.331869
52	4	52	1	topnet_moving.txt	1	0	2026-07-13 14:11:39.388643
53	4	53	1	topnet_hosting.pdf	1	0	2026-07-13 14:11:39.449728
54	4	54	1	topnet_security.docx	1	0	2026-07-13 14:11:39.530169
55	4	55	1	topnet_speed.txt	1	0	2026-07-13 14:11:39.570505
56	6	59	1	utm_programs.pdf	2	0	2026-07-14 09:32:47.922964
57	6	60	1	utm_admissions.txt	2	0	2026-07-14 09:32:47.999193
58	6	61	1	utm_fees_and_scholarships.docx	2	0	2026-07-14 09:32:48.13653
59	6	62	1	utm_library.txt	2	0	2026-07-14 09:32:48.210408
60	6	63	1	utm_it_support.pdf	2	0	2026-07-14 09:32:48.316267
61	6	64	1	utm_examinations.docx	2	0	2026-07-14 09:32:48.422365
62	5	65	1	fiat_warranty.pdf	2	0	2026-07-14 09:46:58.197184
63	5	66	1	fiat_servicing.txt	2	0	2026-07-14 09:46:58.347273
64	5	67	1	fiat_parts_and_repairs.docx	2	0	2026-07-14 09:46:58.585368
65	5	68	1	fiat_roadside_assistance.txt	2	0	2026-07-14 09:46:58.696211
66	5	69	1	fiat_purchase_and_financing.pdf	2	0	2026-07-14 09:46:58.901291
67	8	70	24	02_pii_redaction.txt	2	0	2026-07-14 12:53:41.53082
68	8	71	1	globalnet_plans.txt	1	0	2026-07-25 19:45:15.626356
69	8	72	1	globalnet_billing.txt	1	0	2026-07-25 19:45:15.681797
70	8	73	1	globalnet_support.txt	1	0	2026-07-25 19:45:15.759516
71	8	74	1	globalnet_installation.pdf	2	0	2026-07-25 19:45:15.896694
72	8	75	1	globalnet_business.docx	2	0	2026-07-25 19:45:16.035197
\.


--
-- Data for Name: llm_providers; Type: TABLE DATA; Schema: public; Owner: orange
--

COPY public.llm_providers (id, display_name, provider_key, base_url, api_key_encrypted, model_name, enabled, is_free, rate_limit_rpm, rate_limit_rpd, priority, default_temperature, max_output_tokens, company_id, created_by, created_at, unavailable_until, last_error, rate_limit_group) FROM stdin;
7	Llama 3.3 70B (NVIDIA)	nvidia_nim	https://integrate.api.nvidia.com/v1	gAAAAABqVOu0UIbj7VP4ahnbjD8RxltYChWlrXsJws-Y3nXIUNXMWQWlLqzAKoJDAzVE9trkwsMK603jMhoiWQhsDpnroG1kAvftElqIfegFe7ROiD_BYsnNaOpc2i6qaTtHssRlRU9GAsA-ivujxh_f0rIO1X_6AZB7X_vj_PiCIz0qTPNhZko=	meta/llama-3.3-70b-instruct	t	t	40	1000	40	0.2	1024	\N	1	2026-07-13 13:44:20.2424	2026-08-02 20:05:03.043214	timed out	\N
1	Llama 3.3 70B (Groq)	groq	https://api.groq.com/openai/v1	gAAAAABqTsyNEfegKEAS1nQuTqu6Q4DAALvAKzZ1fqqdQredn9prU6V2A598w59n3v6KOCShG8bSJGqv6G3CEjJ_DHuAzGQ5ticYt-AzdwEmDYjGVfaWmDxSkwg-PMJFaWJjpczcjE9P7zUCP754EZPuANnGKlbZ9Q==	llama-3.3-70b-versatile	t	t	30	1000	20	0.2	1024	\N	\N	2026-07-08 11:28:13.785502	\N	\N	\N
3	Mistral Small	mistral	https://api.mistral.ai/v1	gAAAAABqTsyN_9kjbTxHLEgL3nkc8k5fMjstwVGjMdAkWcy_L0YVQSuTMn1QEnndmhrpT9gAZn7lHN1T1HPxdbbuc9lo9WRz77sUKxiUM7D3XwHneBBhwzi6QUnNBUwv9axjjerIcCfO	mistral-small-latest	t	t	60	1000	30	0.2	1024	\N	\N	2026-07-08 22:17:49.841998	\N	\N	\N
6	GPT-OSS 120B	cerebras	https://api.cerebras.ai/v1	gAAAAABqVOh4DLe8mkKg2G4qHj7icdhzQjVQs6k5Ce3HHIU18JXuzFQw9wrT2RwJulj8c-BEba3WKyyg_SoxJVGCzZ6LEiXflqIxruM-iT_dHCTb7hJIZMJCLfw0ga9lo0zyBS6_GtkBjbxU51mGhUgZqhOpWAkRXQ==	gpt-oss-120b	t	t	30	1000	10	0.3	1024	\N	1	2026-07-13 13:30:32.704065	2026-08-03 10:27:23.17831	at capacity	\N
5	Hy3	openrouter	https://openrouter.ai/api/v1	gAAAAABqVVI-LXfuG5ro8_hxHgv1nYgh_VvwdOfjYFPbYz8vtIzaWsyu83b9WObSsjtQhtTtdPJpQwBnWVnbPkO2BvzqksB0jMw5CoHghxh9cDXYKeZkG2LFazabsAuYx0Zl3sDe9VS3QaIiNwWBU1LOf0N0oxHUCgHb0j9FVj9kDtkDYqkKIEk=	tencent/hy3:free	t	t	20	1000	92	0.2	1024	\N	1	2026-07-13 13:25:11.69967	\N	\N	\N
16	Local Ollama	ollama	http://localhost:11434/v1	gAAAAABqZQ_3q8rspSH836fS314ieBxI0VsRL4r-WXnLSBl6Ce3pKfvdWocJbudSSkHj8B9kd_8Wnqhu5ch4BPQiQ6LnQ81yoQ==	qwen2.5:3b-instruct	t	t	50	5000	100	0.2	1024	\N	1	2026-07-25 19:35:19.594303	\N	\N	\N
17	Laguna XS 2.1	openrouter	https://openrouter.ai/api/v1	gAAAAABqZRac6zBuSjp5EOv0JGDi2UyYOrJZHZpxpTREXTcLYBAz3OQxNWitJY0VM2v4ap39rNXywUITRCMAyeYqFZUsaw8j9aazvJhbkPM5YOyNaIJKy12A3koHrujnOUN3EbHD6C3LtsMBsO2PktTqdQukZNAgInZ5Cq5OCj1d1zfSPSp1rr8=	poolside/laguna-xs-2.1:free	t	t	50	5000	100	0.2	1024	\N	1	2026-07-25 20:03:40.038383	\N	\N	\N
2	Gemini 2.0 Flash	gemini	\N	gAAAAABqTsyN1GwDVGthPyv_BCmyv8POAT-ajjGGH2bULnoSQNv0CGF_Fr8mKmARHzcK2k4HbL7UevwUOqOt_W9SjjXtFJWeODpRy7ks0Z14FsHlKBQcBcqmevjtgLi70L3E6mCCJNqiJoR_tqB0QC2T2rafeJrY6w==	gemini-2.0-flash	t	t	15	1500	90	0.2	1024	\N	\N	2026-07-08 22:17:49.833442	2026-08-02 21:03:47.367204	at capacity	\N
4	Llama 3.3 70B	openrouter	https://openrouter.ai/api/v1	gAAAAABqVVI-U_y3klqoL3yI6o2lockf6kvg9UT0YweMk7D3KRSJnNHebsM6-q_1Ss1hyer7dvEpLRp3q5f5SOwOqPeAqUOvt8x4gJCVs-wi1NI_92FbVKFiSvO1YkjJgft4ZTRInZuA8_8jDxucPUxL2cVOduaD9aeecRBPAZrMq2Ep5HOcYMs=	meta-llama/llama-3.3-70b-instruct:free	t	t	20	50	91	0.2	1024	\N	\N	2026-07-08 22:17:49.843428	2026-08-02 20:05:03.96418	unavailable	\N
8	Qwen3 Next 80B	openrouter	https://openrouter.ai/api/v1	gAAAAABqVVI-UqH1zxtZiAaB5Px8mREFB568iGEmb6Th9LDDypcA2Lr5OGVADBh0ZCIFbW08uxnUrwD_VJgcVH3MiKso51PFifujA3bKp43oS8t6TsFVLYB4FpLVjUbCnYsIBWNOp3TcLKNcX8BwgefnDUkbF7vmzg1QO_52s8rRrQ2nqDFaSYQ=	qwen/qwen3-next-80b-a3b-instruct:free	t	t	20	50	45	0.2	1024	\N	1	2026-07-13 19:24:48.153827	2026-07-13 22:02:05.774778	at capacity	\N
9	Nemotron 3 Super 120B	openrouter	https://openrouter.ai/api/v1	gAAAAABqVVI-87OP3vgRgMn9FT4LT2tFPKNgNrl1db-5m3WJxHecO-4kOmv5nABnQl17a3kjxehz2jiyTFLD8YaU7V-HpNeyGhahzVLGqfHfJUYbrGbdCLO0sTfaYufas_E_hVujvgU9qTv5rr-RhR9HkWYXSLGuwqMDIeTJeVcsrFEN9cFBR0M=	nvidia/nemotron-3-super-120b-a12b:free	t	t	20	50	46	0.2	1024	\N	1	2026-07-13 19:43:38.348672	\N	\N	\N
\.


--
-- Data for Name: messages; Type: TABLE DATA; Schema: public; Owner: orange
--

COPY public.messages (id, conversation_id, role, content, created_at, sources, feedback, provider_id) FROM stdin;
1	1	user	How much does the Fiber Pro plan cost and what internet speed does it include?	2026-07-08 22:21:01.951085	\N	\N	\N
3	2	user	How much does the Ooredoo Hayya prepaid plan cost?	2026-07-08 22:21:31.959831	\N	\N	\N
5	4	user	What is the refund policy?	2026-07-13 10:13:09.441491	\N	\N	\N
7	6	user	What is the refund policy?	2026-07-13 10:13:15.595891	\N	\N	\N
9	8	user	What is the refund policy?	2026-07-13 10:20:14.457241	\N	\N	\N
11	9	user	What is the refund policy?	2026-07-13 10:20:15.325742	\N	\N	\N
13	10	user	What is the refund policy?	2026-07-13 10:20:16.266709	\N	\N	\N
15	11	user	What is the refund policy?	2026-07-13 10:20:16.764191	\N	\N	\N
17	12	user	What is the refund policy?	2026-07-13 10:20:18.755739	\N	\N	\N
19	15	user	good morning	2026-07-13 10:23:38.661423	\N	\N	\N
23	17	user	What is the refund policy?	2026-07-13 10:36:36.772626	\N	\N	\N
25	18	user	What is the refund policy?	2026-07-13 10:36:37.469642	\N	\N	\N
29	8	user	can you tell me the name of the company i work for	2026-07-13 13:18:42.015292	\N	\N	\N
31	8	user	what do you know about the company i work for	2026-07-13 13:18:57.696404	\N	\N	\N
33	8	user	what is the opening hours of bit	2026-07-13 13:19:25.829491	\N	\N	\N
35	24	user	What is the refund policy?	2026-07-13 13:35:01.015882	\N	\N	\N
37	25	user	What is the refund policy?	2026-07-13 13:35:18.660782	\N	\N	\N
39	27	user	good mrning	2026-07-13 13:35:48.896598	\N	\N	\N
41	28	user	good morning	2026-07-13 13:45:43.640667	\N	\N	\N
42	28	assistant	Good morning! I'm a customer-support assistant for BIAT. How can I help you today?	2026-07-13 13:45:43.640672	\N	\N	\N
45	31	user	What is the refund policy?	2026-07-13 13:47:54.825607	\N	\N	\N
47	32	user	What is the refund policy?	2026-07-13 13:52:17.40031	\N	\N	\N
2	1	assistant	The Fiber Pro plan costs 79 euros per month and includes an internet speed of 500 Mbps.	2026-07-08 22:21:01.951092	\N	\N	3
4	2	assistant	I don't have that information in the provided context.	2026-07-08 22:21:31.959835	\N	\N	3
20	15	assistant	Good morning! How can I assist you today?	2026-07-13 10:23:38.661426	\N	\N	3
49	28	user	hey	2026-07-13 14:03:49.897248	\N	\N	\N
50	28	assistant	I’m sorry, I don’t have that information.	2026-07-13 14:03:49.897251	\N	\N	\N
51	34	user	hey	2026-07-13 14:07:04.183917	\N	\N	\N
53	35	user	What is the refund policy?	2026-07-13 14:12:44.493157	\N	\N	\N
54	35	assistant	The refund policy states that a customer can request a refund within 14 days of starting a new subscription (the cooling‑off period). In addition, if a customer downgrades their plan part‑way through a billing cycle, a prorated refund will be issued for the unused portion of the service. No other refund details are provided in the given information.	2026-07-13 14:12:44.49316	\N	\N	\N
55	35	user	What happens if I downgrade my plan halfway through the month?	2026-07-13 14:12:47.555086	\N	\N	\N
56	35	assistant	If you downgrade your plan mid-cycle, you will receive a prorated refund.	2026-07-13 14:12:47.555089	\N	\N	\N
57	36	user	What compensation do I get if there is an outage?	2026-07-13 14:12:51.038311	\N	\N	\N
58	36	assistant	If an unplanned outage exceeds 24 continuous hours, you will receive an automatic credit of one thirtieth of your monthly fee per full day lost. The credit appears on your next invoice and does not need to be claimed.	2026-07-13 14:12:51.038314	\N	\N	\N
59	36	user	How long does the outage have to last before I get a credit?	2026-07-13 14:14:36.960001	\N	\N	\N
60	36	assistant	An unplanned outage must exceed 24 continuous hours before you receive a credit. After that threshold, you receive an automatic credit of one thirtieth of your monthly fee for each full day lost.	2026-07-13 14:14:36.960003	\N	\N	\N
61	37	user	How long is prepaid credit valid for?	2026-07-13 14:14:40.289113	\N	\N	\N
62	37	assistant	Prepaid credit remains valid for **6 months from the date of the last top‑up**.	2026-07-13 14:14:40.289116	\N	\N	\N
63	37	user	What prepaid data packs are available?	2026-07-13 14:14:43.236229	\N	\N	\N
64	37	assistant	The available prepaid data packs are:\n\n1. 1 GB for 2 euros, valid for 7 days\n2. 5 GB for 7 euros, valid for 30 days\n3. 20 GB for 18 euros, valid for 30 days\n\nNote that unused pack data does not roll over.	2026-07-13 14:14:43.236232	\N	\N	\N
65	38	user	How do I raise a complaint and how fast will you respond?	2026-07-13 14:14:46.5943	\N	\N	\N
66	38	assistant	You can raise a complaint by phone, in a store, or via the Telecom mobile app. Every complaint receives a reference number of the form **CMP-YYYY-NNNNNN**.\n\nThe first response to your complaint will be provided within **2 working days**.	2026-07-13 14:14:46.594302	\N	\N	\N
67	38	user	What happens if you miss the deadline?	2026-07-13 14:16:32.534457	\N	\N	\N
68	38	assistant	The context doesn't specify exactly what "miss the deadline" refers to. However, it does describe several deadlines and their consequences:\n\n- **Late payment (billing deadline):** If payment isn't made within 14 days, a 5% late fee is applied, and service may be suspended after 30 days overdue.\n- **Cooling-off period (14 days):** A new subscription or contract can be cancelled without penalty within 14 days; after that, standard cancellation/early termination fees would apply.\n- **Price increase termination (30 days):** A customer has 30 days from the price change notice to terminate without penalty; after that window, they would no longer be able to leave fee-free under that provision.\n- **SMS reset code (10 minutes):** If the reset code isn't used within 10 minutes, it expires.\n- **Equipment return (14 days):** Equipment returned after cancellation must be returned undamaged within 14 days, or it is charged at full retail price.\n\nIf you can clarify which deadline you're asking about, I can give a more specific answer.	2026-07-13 14:16:32.534463	\N	\N	\N
69	39	user	How much data does the Unlimited mobile plan include and what does it cost?	2026-07-13 14:16:35.98791	\N	\N	\N
71	40	user	What is the wallet limit for mobile money?	2026-07-13 14:16:38.948491	\N	\N	\N
72	40	assistant	The wallet limit for Mobile Money is 5000 dinars.	2026-07-13 14:16:38.948495	\N	\N	\N
73	40	user	What does it cost to transfer money to a bank account?	2026-07-13 14:16:42.107829	\N	\N	\N
74	40	assistant	According to the context, transferring money to a bank account costs **1 percent of the transfer amount**, with a **minimum fee of 0.5 dinars**.	2026-07-13 14:16:42.107834	\N	\N	\N
75	41	user	What is the refund policy?	2026-07-13 14:26:11.15704	\N	\N	\N
76	41	assistant	The refund policy is as follows:\n\n- **Cooling‑off period:** A customer can request a refund within 14 days of starting a new subscription. During this period the contract can be cancelled without any penalty.  \n- **Prorated refunds:** If a customer downgrades their plan in the middle of a billing cycle, a prorated refund for the unused portion of the higher‑priced plan will be issued.  \n\nNo other refund details are provided in the available information.	2026-07-13 14:26:11.157044	\N	\N	\N
77	41	user	What happens if I downgrade my plan halfway through the month?	2026-07-13 14:26:14.649179	\N	\N	\N
78	41	assistant	If you downgrade your plan mid-cycle, you will receive a prorated refund.	2026-07-13 14:26:14.649184	\N	\N	\N
79	42	user	What compensation do I get if there is an outage?	2026-07-13 14:26:18.320234	\N	\N	\N
80	42	assistant	If an unplanned outage exceeds 24 continuous hours, you will receive an automatic credit of one thirtieth of your monthly fee per full day lost. The credit appears on your next invoice and does not need to be claimed.	2026-07-13 14:26:18.320238	\N	\N	\N
81	40	user	Do I need to verify my identity?	2026-07-13 14:28:55.279563	\N	\N	\N
82	40	assistant	Yes. Identity verification is required in several cases:\n\n- **Getting a new SIM:** Registration is mandatory, and you must present a national ID card or passport.\n- **Replacing a lost, stolen, or damaged SIM:** You need to bring the ID document used to register the line, as the replacement is only issued to the registered owner.\n- **Number portability:** You must bring your ID document when porting an existing number to Ooredoo.	2026-07-13 14:28:55.279567	\N	\N	\N
83	43	user	How does the family plan discount work?	2026-07-13 14:28:59.096471	\N	\N	\N
84	43	assistant	The family plan lets up to 5 lines share a single invoice. The first line is charged the regular (full‑price) rate. Every additional line added to the plan receives a **30 % discount** on its monthly price.	2026-07-13 14:28:59.096476	\N	\N	\N
85	43	user	How many lines can I have on one family plan?	2026-07-13 14:29:02.082192	\N	\N	\N
86	43	assistant	You can have up to 5 lines under one family plan. The first line pays full price, and each additional line receives a 30 percent discount.	2026-07-13 14:29:02.082195	\N	\N	\N
87	44	user	What does Device Care cover and how much is it?	2026-07-13 14:29:05.806714	\N	\N	\N
88	44	assistant	Device Care costs 7 dinars per month and covers accidental damage, liquid damage, and theft.	2026-07-13 14:29:05.806719	\N	\N	\N
89	42	user	How long does the outage have to last before I get a credit?	2026-07-13 14:29:17.096647	\N	\N	\N
97	44	user	What is the excess for a screen repair?	2026-07-13 14:31:11.608612	\N	\N	\N
90	42	assistant	An unplanned outage must exceed 24 continuous hours before you receive a credit. Once it passes that threshold, you receive an automatic credit of one thirtieth of your monthly fee for each full day lost.	2026-07-13 14:29:17.09665	\N	\N	\N
91	45	user	How long is prepaid credit valid for?	2026-07-13 14:29:20.243202	\N	\N	\N
92	45	assistant	Prepaid credit remains valid for 6 months from the date of the most recent top‑up.	2026-07-13 14:29:20.243206	\N	\N	\N
93	45	user	What prepaid data packs are available?	2026-07-13 14:29:24.784897	\N	\N	\N
94	45	assistant	The available prepaid data packs are: \n1. 1 GB for 2 euros, valid for 7 days\n2. 5 GB for 7 euros, valid for 30 days\n3. 20 GB for 18 euros, valid for 30 days.	2026-07-13 14:29:24.784913	\N	\N	\N
95	46	user	What is the wallet limit for mobile money?	2026-07-13 14:29:28.35111	\N	\N	\N
96	46	assistant	The wallet limit for Ooredoo Mobile Money is 5000 dinars.	2026-07-13 14:29:28.351116	\N	\N	3
98	44	assistant	The excess for a screen repair is 50 dinars.	2026-07-13 14:31:11.608615	\N	\N	\N
99	47	user	I am a student. What offers do you have?	2026-07-13 14:31:14.736113	\N	\N	\N
100	47	assistant	As a student you can qualify for Ooredoo’s **Youth plan**. It provides:\n\n- **40 GB of data** each month  \n- **Unlimited calls and SMS**  \n- **Price:** 22 dinars per month  \n\nAdditional benefits:\n\n- Free data for study platforms  \n- Campus Wi‑Fi roaming at partner universities  \n\nEligibility – you must be aged 16‑25 and present a valid student card. Proof of enrolment has to be resubmitted each academic year by 31 October. If the proof lapses, the line will revert to the standard plan (32 dinars) and you’ll be notified 14 days in advance.  \n\nNote: a Youth line cannot be part of a family‑plan pool at the same time.	2026-07-13 14:31:14.736117	\N	\N	\N
101	47	user	What happens if I don't renew my proof of enrolment?	2026-07-13 14:31:17.685278	\N	\N	\N
102	47	assistant	If your proof of enrolment lapses, your Youth plan will revert to the standard plan at 32 dinars per month, and you will be notified 14 days beforehand.	2026-07-13 14:31:17.685281	\N	\N	\N
103	48	user	How many times can I transfer my eSIM to a new device?	2026-07-13 14:31:20.955197	\N	\N	\N
104	48	assistant	You can transfer your eSIM to a new device up to 3 times per year at no charge.	2026-07-13 14:31:20.955202	\N	\N	\N
105	48	user	What if my old phone is broken?	2026-07-13 14:33:30.877362	\N	\N	\N
106	48	assistant	I don't have enough information in the provided context to answer that specific question.\n\nHowever, if you're referring to Ooredoo **Device Care and Insurance**, here's what the context does say about device damage and eligibility:\n\n- **Device Care** covers accidental damage, liquid damage, and theft for **7 dinars per month**.\n- It must be taken out **within 30 days** of buying the device.\n- **Devices older than 36 months are not eligible.**\n- If you have Device Care, the excess is **50 dinars for a screen repair** and **120 dinars for a full replacement**.\n- Repairs are completed within **5 working days**, and a **loan handset is provided free** during the repair.\n\nIf your old phone is already broken and you don't have Device Care, the provided context doesn't include information about repair options for that situation.	2026-07-13 14:33:30.87737	\N	\N	\N
107	49	user	What are your call centre hours and what number do I call?	2026-07-13 14:33:34.109124	\N	\N	\N
109	50	user	Can I get a free signal booster if my indoor signal is weak?	2026-07-13 14:33:37.241385	\N	\N	\N
111	51	user	How much can I borrow for a mortgage and over how long?	2026-07-13 14:33:40.670915	\N	\N	\N
113	53	user	what is the cost of a monthly plan	2026-07-13 19:39:57.046409	\N	\N	\N
115	55	user	can you tell me the working hours of biat	2026-07-13 19:47:13.535061	\N	\N	\N
117	55	user	okay thank you have a good day	2026-07-13 19:47:25.934941	\N	\N	\N
119	55	user	you too	2026-07-13 19:47:33.916072	\N	\N	\N
121	56	user	good evening	2026-07-13 19:47:55.049526	\N	\N	\N
123	57	user	read this	2026-07-13 19:55:35.420488	\N	\N	\N
125	57	user	can you inform me what my document has	2026-07-13 19:55:45.880818	\N	\N	\N
127	58	user	hey if i give you a file can you read it	2026-07-13 19:58:52.731276	\N	\N	\N
129	58	user	­	2026-07-13 19:59:04.099586	\N	\N	\N
131	59	user	who is the client mentioned here	2026-07-13 19:59:45.758271	\N	\N	\N
133	62	user	good morning	2026-07-14 10:05:10.759972	\N	\N	\N
135	63	user	good morning	2026-07-14 10:05:41.093175	\N	\N	\N
137	65	user	good morning	2026-07-16 09:04:20.927834	\N	\N	\N
139	66	user	good morning	2026-07-16 09:05:19.582736	\N	\N	\N
140	66	assistant	I don’t have that information.	2026-07-16 09:05:19.58274	\N	\N	\N
141	66	user	good morning	2026-07-16 09:05:25.673601	\N	\N	\N
142	66	assistant	Good morning. How can I assist you today?	2026-07-16 09:05:25.673604	\N	\N	\N
143	66	user	hello	2026-07-16 09:05:33.835175	\N	\N	\N
144	66	assistant	I don’t have that information.	2026-07-16 09:05:33.835179	\N	\N	\N
145	67	user	good morning	2026-07-16 09:08:44.025593	\N	\N	\N
147	67	user	can you tell me how i am supposed to take a loan	2026-07-16 09:09:00.792979	\N	\N	\N
122	56	assistant	Good evening! How can I assist you today?	2026-07-13 19:47:55.049529	\N	\N	3
149	68	user	Is there a data cap on the unlimited plan?	2026-07-12 15:26:21	\N	\N	\N
151	68	user	What happens if I go over 2 TB in a month?	2026-07-12 15:27:47	\N	\N	\N
153	69	user	What is the wallet limit for mobile money?	2026-07-12 13:08:06	\N	\N	\N
155	69	user	Do I need to verify my identity?	2026-07-12 13:10:43	\N	\N	\N
157	70	user	How much does the Fiber Pro plan cost?	2026-07-12 08:41:40	\N	\N	\N
159	70	user	Does it come with a router?	2026-07-12 08:42:29	\N	\N	\N
161	71	user	What TV bundles do you offer?	2026-07-14 14:35:08	\N	\N	\N
163	72	user	How does the family plan discount work?	2026-07-14 09:24:58	\N	\N	\N
165	73	user	What documents do I need to open a business account?	2026-07-14 16:15:28	\N	\N	\N
167	74	user	What interest does the savings account pay?	2026-07-14 10:20:40	\N	\N	\N
169	75	user	What are the fees for an international transfer?	2026-07-14 12:13:30	\N	\N	\N
171	75	user	And what does a card replacement cost?	2026-07-14 12:14:20	\N	\N	\N
173	76	user	What compensation do I get if there is an outage?	2026-07-14 09:18:54	\N	\N	\N
175	77	user	How do loyalty points work?	2026-07-15 14:47:13	\N	\N	\N
177	77	user	Do the points expire?	2026-07-15 14:49:16	\N	\N	\N
179	78	user	What is your refund policy?	2026-07-15 11:29:01	\N	\N	\N
181	79	user	What does Device Care cover?	2026-07-15 11:12:40	\N	\N	\N
183	80	user	How much is a static IP address?	2026-07-15 16:57:03	\N	\N	\N
185	81	user	Is there a data cap on the unlimited plan?	2026-07-15 16:23:24	\N	\N	\N
187	81	user	What happens if I go over 2 TB in a month?	2026-07-15 16:25:21	\N	\N	\N
189	82	user	What is the wallet limit for mobile money?	2026-07-15 09:34:41	\N	\N	\N
191	82	user	Do I need to verify my identity?	2026-07-15 09:35:26	\N	\N	\N
193	83	user	What prepaid mobile plans do you have and how much data do they include?	2026-07-16 09:40:33.640344	\N	\N	\N
195	85	user	goodm orni	2026-07-20 08:58:14.385315	\N	\N	\N
197	86	user	good morning	2026-07-20 08:58:20.145937	\N	\N	\N
36	24	assistant	The refund policy is as follows:\n\n- **Cooling‑off period:** A customer can request a refund within 14 days of starting a new subscription.  \n- **Plan downgrades:** If a customer downgrades their plan in the middle of a billing cycle, a prorated refund will be issued for the unused portion of the higher‑priced plan.	2026-07-13 13:35:01.015885	\N	\N	6
146	67	assistant	Good morning! How can I assist you today?	2026-07-16 09:08:44.025597	\N	down	6
267	135	user	What home internet options are available?	2026-08-02 20:04:21.314996	\N	\N	\N
8	6	assistant	The refund policy includes two parts:\n\n1. **Cooling-off period**: A customer may request a refund within 14 days of a new subscription activation.\n2. **Prorated refunds**: Issued when downgrading a plan mid-cycle.	2026-07-13 10:13:15.595893	\N	\N	3
52	34	assistant	Hello! How can I assist you today?	2026-07-13 14:07:04.18392	\N	\N	3
112	51	assistant	According to the context, BIAT lends up to **80 percent of a property's value** for a **maximum term of 25 years** for mortgages.	2026-07-13 14:33:40.670918	\N	\N	3
168	74	assistant	The savings account pays 5.2% annual interest, calculated daily and credited quarterly. There is no minimum balance requirement.	2026-07-14 10:20:45	\N	\N	3
176	77	assistant	You earn 1 point per dinar spent on your monthly bill. Points can be redeemed for device discounts starting at 500 points, and they expire after 24 months.	2026-07-15 14:47:22	\N	\N	3
178	77	assistant	Yes, loyalty points expire 24 months after they are earned. You'll get a reminder SMS 30 days before any points lapse.	2026-07-15 14:49:28	\N	\N	3
6	4	assistant	According to the context, the refund policy is as follows: \n\n- A customer may request a refund within 14 days of a new subscription (cooling-off period).\n- Prorated refunds are issued when downgrading a plan mid-cycle.\n- For equipment, if not returned within 14 days of cancellation, an unreturned router is charged at 120 euros and an unreturned set-top box at 80 euros. During the cooling-off period, equipment must be returned undamaged, or it is charged at its full retail price. \n\nAdditionally, credits for service incidents can be requested through the business portal within 30 days of the incident, up to 50 percent of the monthly fee.	2026-07-13 10:13:09.441495	\N	\N	1
10	8	assistant	I don't have that information. The provided context does not mention a refund policy. It discusses card safety, liability, transactions, and loan terms, but does not include information about refunds.	2026-07-13 10:20:14.457243	\N	\N	1
12	9	assistant	I don't have that information. The context only discusses billing, payments, and suspension policies, but does not mention a refund policy.	2026-07-13 10:20:15.325745	\N	\N	1
14	10	assistant	According to the context, the refund policy is as follows: \n\n- A customer may request a refund within 14 days of a new subscription (cooling-off period).\n- Prorated refunds are issued when downgrading a plan mid-cycle.\n- If a price increase exceeds the rate of inflation, the customer may terminate the contract without an early termination fee within 30 days of the notice.\n- For business customers, credits are requested through the business portal within 30 days of the incident, with a value of up to 50 percent of the monthly fee.	2026-07-13 10:20:16.266712	\N	\N	1
16	11	assistant	I don't have that information. The provided context does not mention a refund policy.	2026-07-13 10:20:16.764194	\N	\N	1
18	12	assistant	According to the context, the refund policy is as follows: \n\n- A customer may request a refund within 14 days of a new subscription (cooling-off period).\n- Prorated refunds are issued when downgrading a plan mid-cycle.\n- If a price increase exceeds the rate of inflation, the customer may terminate the contract without an early termination fee within 30 days of the notice.\n- For business customers, credits are requested through the business portal within 30 days of the incident, with a value of up to 50 percent of the monthly fee.	2026-07-13 10:20:18.755742	\N	\N	1
24	17	assistant	According to the context, the refund policy is as follows: \n\n- A customer may request a refund within 14 days of a new subscription (cooling-off period).\n- Prorated refunds are issued when downgrading a plan mid-cycle.\n- If a price increase exceeds the rate of inflation, the customer may terminate the contract without an early termination fee within 30 days of the notice.\n- For business customers, credits are requested through the business portal within 30 days of the incident, with a value of up to 50 percent of the monthly fee.	2026-07-13 10:36:36.772628	\N	\N	1
26	18	assistant	I don't have that information. The provided context only discusses billing, payments, and suspension policies, but does not mention a refund policy.	2026-07-13 10:36:37.469645	\N	\N	1
30	8	assistant	I don't have that information.	2026-07-13 13:18:42.015295	\N	\N	1
32	8	assistant	I don't have that information. No relevant documents were found, so I'm unable to provide any details about the company you work for.	2026-07-13 13:18:57.696407	\N	\N	1
34	8	assistant	The opening hours of BIAT branches are:\n\n- Monday to Friday: 8am to 4pm, with a break from 1pm to 2pm at smaller branches.\n- Saturday: 8am to noon, but only at selected branches in Tunis, Sfax, and Sousse.\n- Branches are closed on public holidays.\n\nDuring July and August, branches operate from 7:30am to 1:30pm, and during Ramadan from 8am to 2pm.	2026-07-13 13:19:25.829496	\N	\N	1
110	50	assistant	You can request a free signal booster if you're experiencing a weak indoor signal, but it's subject to a technical survey. If the survey finds no fault on the network side, the booster will be offered at 39 dinars instead of being free.	2026-07-13 14:33:37.241388	\N	\N	1
114	53	assistant	The cost of a monthly plan varies depending on the type of plan. Here are the costs mentioned in the context:\n\n- Mobile plans: \n  - Start: 10 euros/month\n  - Plus: 20 euros/month\n  - Unlimited: 35 euros/month\n- Business Mobile plans: \n  - Business Mobile Start: 18 euros/line/month\n  - Business Mobile Pro: 30 euros/line/month\n- Home internet plans: \n  - Fiber Lite: 49 euros/month\n  - Fiber Pro: 79 euros/month\n  - Fiber Max: 99 euros/month\n- Business Fiber: 149 euros/month	2026-07-13 19:39:57.046413	\N	\N	1
150	68	assistant	The unlimited plan has no hard cap, but a 2 TB monthly fair-use threshold. Beyond it, speeds may be reduced during peak hours.	2026-07-12 15:26:29	\N	\N	1
152	68	assistant	Nothing is charged extra — your speed may simply be prioritised lower during peak hours (19:00-23:00) until the next billing cycle.	2026-07-12 15:27:58	\N	\N	1
154	69	assistant	The standard mobile money wallet is capped at 500 TND. With identity verification, the limit rises to 5,000 TND.	2026-07-12 13:08:17	\N	\N	1
156	69	assistant	Verification is optional for the basic wallet, but required for the 5,000 TND limit and for transfers to bank accounts. You can verify in any branch with your CIN.	2026-07-12 13:10:51	\N	\N	1
166	73	assistant	You'll need the company's registration certificate, tax identification, the manager's CIN, and proof of address. Opening takes 3-5 business days.	2026-07-14 16:15:35	\N	\N	1
184	80	assistant	A static IPv4 address is 10 TND per month on residential plans, and included free on all business plans.	2026-07-15 16:57:12	\N	\N	1
38	25	assistant	The refund policy is as follows:\n\n- **Cooling‑off period:** A customer can request a refund within 14 days of starting a new subscription.  \n- **Prorated refunds:** If a customer downgrades their plan part‑way through a billing cycle, a prorated refund will be issued for the unused portion of the service.  \n\nNo other refund details are provided in the available information.	2026-07-13 13:35:18.660786	\N	\N	6
40	27	assistant	Good morning! How can I assist you today?	2026-07-13 13:35:48.896601	\N	\N	6
48	32	assistant	The refund policy is as follows:\n\n- **Cooling‑off period:** A customer can request a refund within 14 days of starting a new subscription.  \n- **Prorated refunds:** If a plan is downgraded part‑way through a billing cycle, a prorated refund will be issued for the unused portion of the higher‑priced plan.	2026-07-13 13:52:17.400314	\N	\N	6
70	39	assistant	The Unlimited mobile plan provides unlimited data and costs 35 euros per month.	2026-07-13 14:16:35.987914	\N	\N	6
108	49	assistant	Based on the information provided:\n\n- **Call‑centre hours:** 8 am to 10 pm, 7 days a week.  \n- **Number to call:** Dial **1200** from an Ooredoo line (the call is free of charge).\n\n(Additionally, another part of the context mentions a 24 / 7 call centre reachable on **1111** from an Ooredoo line, also free of charge.)	2026-07-13 14:33:34.109142	\N	\N	6
116	55	assistant	BIAT’s **branch opening hours** are:\n\n- **Monday – Friday:** 8 am – 4 pm (smaller branches have a 1 pm – 2 pm lunch break).  \n- **Saturday:** 8 am – 12 pm at selected branches in Tunis, Sfax and Sousse.  \n- **Public holidays:** branches are closed.  \n\n**Seasonal adjustments**\n\n- **July – August:** a single session from 7:30 am – 1:30 pm.  \n- **Ramadan:** 8 am – 2 pm.  \n\nThe exact hours for each specific branch are listed in the BIAT Net app.\n\n**ATMs** and the BIAT Net service are available **24 / 7**, except during a scheduled maintenance window on Sundays from 2 am to 4 am.	2026-07-13 19:47:13.535064	\N	\N	6
118	55	assistant	You’re welcome! Have a great day!	2026-07-13 19:47:25.934945	\N	\N	6
120	55	assistant	I’m sorry, but I don’t have information on that.	2026-07-13 19:47:33.916075	\N	\N	6
124	57	assistant	I’m sorry, but I don’t have any information on that.	2026-07-13 19:55:35.420491	\N	\N	6
126	57	assistant	I’m sorry, but I don’t have that information.	2026-07-13 19:55:45.880821	\N	\N	6
128	58	assistant	I don’t have that information.	2026-07-13 19:58:52.731278	\N	\N	6
130	58	assistant	I’m sorry, but I don’t have that information.	2026-07-13 19:59:04.099589	\N	\N	6
132	59	assistant	I don’t have that information.	2026-07-13 19:59:45.758274	\N	\N	6
134	62	assistant	I’m sorry, but I don’t have that information.	2026-07-14 10:05:10.759975	\N	\N	6
194	83	assistant	Sure! Our prepaid mobile options are:\n\n- **Hayya** – 3 GB of data for 10 dinars per month.  \n- **Hayya Plus** – 15 GB of data for 25 dinars per month.	2026-07-16 09:40:33.640347	\N	\N	6
138	65	assistant	I’m sorry, but I don’t have that information.	2026-07-16 09:04:20.927837	\N	up	6
148	67	assistant	Sure! Here’s how you can obtain a loan with BI BIAT:\n\n1. **Check Eligibility**  \n   * You must be a BIAT customer with a salary domiciled at BIAT for at least 3 months.  \n   * Hold a permanent employment contract **or** have at least 2 years of self‑employment accounts.  \n   * Be under 65 years old at the end of the loan term.  \n   * Your total monthly repayments (across all credit) may not exceed 40 % of your net monthly income.\n\n2. **Gather the Required Documents**  \n   * National ID.  \n   * The last 3 payslips.  \n   * An employer certificate.  \n   * The last 3 months of account statements.  \n   * Proof of address.\n\n3. **Submit Your Application**  \n   * Bring the documents to your BIAT branch (or submit them through the bank’s channels, if available).  \n\n4. **Decision & Funding**  \n   * BIAT will give you a decision within **5 business days** after receiving a complete file.  \n   * Once you sign the loan agreement, the funds will be released within **2 business days**.\n\n5. **Loan Terms (example: Personal Loan)**  \n   * Amounts: 1 000 – 30 000 dinars.  \n   * Term: 12 – 60 months.  \n   * Fixed annual rate: starting at 9.5 % (depends on term and profile).  \n   * File fee: 1 % of the loan amount (minimum 30 dinars).  \n\n6. **Early Repayment (if needed)**  \n   * You may repay the loan early, in whole or in part.  \n   * An early‑repayment fee of 1 % of the amount repaid ahead of schedule applies, but it is waived during the final 12 months of the term.\n\nIf you have any specific questions about the loan amount, term, or rates, feel free to let me know!	2026-07-16 09:09:00.792982	\N	\N	6
158	70	assistant	The Fiber Pro plan is 89 TND per month and includes 500 Mbps download speed. Installation is free if you sign a 12-month contract.	2026-07-12 08:41:49	\N	\N	6
160	70	assistant	Yes — a WiFi 6 router is included at no extra cost and remains yours after the contract period ends.	2026-07-12 08:42:40	\N	\N	6
170	75	assistant	International transfers cost 0.5% of the amount with a 20 TND minimum. Transfers within the SEPA zone settle in 1-2 business days.	2026-07-14 12:13:42	\N	\N	6
172	75	assistant	A replacement card is 15 TND for standard delivery, or 30 TND for express delivery within 48 hours.	2026-07-14 12:14:26	\N	\N	6
182	79	assistant	Device Care covers accidental damage, liquid damage and theft, for 12 TND per month. Screen repairs carry a 50 TND excess.	2026-07-15 11:12:48	\N	\N	6
186	81	assistant	The unlimited plan has no hard cap, but a 2 TB monthly fair-use threshold. Beyond it, speeds may be reduced during peak hours.	2026-07-15 16:23:36	\N	\N	6
188	81	assistant	Nothing is charged extra — your speed may simply be prioritised lower during peak hours (19:00-23:00) until the next billing cycle.	2026-07-15 16:25:30	\N	\N	6
46	31	assistant	According to the provided context, the refund policy is as follows:\n\n- **Cooling-off period:** A customer may request a refund within 14 days of a new subscription.\n- **Plan downgrade:** Prorated refunds are issued when downgrading a plan mid-cycle.	2026-07-13 13:47:54.825611	\N	\N	7
136	63	assistant	Good morning. How can I assist you today?	2026-07-14 10:05:41.093178	\N	\N	7
162	71	assistant	Two bundles: Essential (60 channels, 15 TND/month) and Premium (120 channels plus sports, 35 TND/month). Both allow streaming on up to 3 devices.	2026-07-14 14:35:15	\N	\N	7
190	82	assistant	The standard mobile money wallet is capped at 500 TND. With identity verification, the limit rises to 5,000 TND.	2026-07-15 09:34:45	\N	\N	7
192	82	assistant	Verification is optional for the basic wallet, but required for the 5,000 TND limit and for transfers to bank accounts. You can verify in any branch with your CIN.	2026-07-15 09:35:37	\N	\N	7
164	72	assistant	Each additional line on a family plan gets 20% off its monthly fee, up to 5 lines. All lines share the plan's data allowance.	2026-07-14 09:25:05	\N	\N	8
174	76	assistant	If an outage lasts more than 4 consecutive hours, you receive a credit equal to one day of your subscription for each day affected, applied automatically.	2026-07-14 09:19:01	\N	\N	2
180	78	assistant	You can request a full refund within 14 days of activation. After that, refunds are prorated for the unused portion of the current billing month.	2026-07-15 11:29:12	\N	\N	4
199	87	user	Cuanto cuesta el plan Business Fiber y que garantia de tiempo de actividad tiene?	2026-07-23 21:15:47.970905	\N	\N	\N
200	87	assistant	El plan Business Fiber cuesta 149 euros al mes. En cuanto a la garantía de tiempo de actividad, el plan Business Fiber tiene un acuerdo de nivel de servicio (SLA) que garantiza un tiempo de actividad del 99,9% medido mensualmente. Esto significa que si el tiempo de actividad cae por debajo de este porcentaje, el cliente puede solicitar un crédito del 10% del cargo mensual por cada 0,1% por debajo del objetivo, hasta un máximo del 50% del cargo mensual.	2026-07-23 21:15:47.975874	[{"document_id": 13, "filename": "telecom_business.docx", "score": 0.8232}, {"document_id": 1, "filename": "telecom_plans.txt", "score": 0.7117}]	\N	1
201	90	user	Quels sont les forfaits mobiles disponibles et combien coute le forfait illimite?	2026-07-23 21:16:29.860072	\N	\N	\N
202	90	assistant	Bonjour ! Nous proposons trois forfaits mobiles : Start, Plus et Unlimited. Le forfait Unlimited coûte 35 euros par mois et offre une quantité de données illimitée, ainsi que des appels et des SMS illimités dans le pays. Les autres forfaits sont le Start, qui coûte 10 euros par mois pour 5 GB de données, et le Plus, qui coûte 20 euros par mois pour 30 GB de données. Tous les forfaits mobiles incluent des appels et des SMS illimités dans le pays.	2026-07-23 21:16:29.863258	[{"document_id": 1, "filename": "telecom_plans.txt", "score": 0.7161}, {"document_id": 4, "filename": "telecom_roaming.txt", "score": 0.6715}, {"document_id": 13, "filename": "telecom_business.docx", "score": 0.6355}]	\N	1
203	91	user	Jakie sa plany biznesowe i ile kosztuje Business Fiber?	2026-07-23 21:16:45.314877	\N	\N	\N
204	91	assistant	W ofercie Telecom znajdują się trzy plany biznesowe: Business Mobile Start, Business Mobile Pro oraz Business Fiber. Plan Business Fiber oferuje szybkość 1 Gbps symmetriczną i kosztuje 149 euro miesięcznie. Dodatkowo, klienci z 5 lub więcej liniami otrzymują 10% zniżkę, a klienci z 20 lub więcej liniami otrzymują 20% zniżkę.	2026-07-23 21:16:45.318025	[{"document_id": 13, "filename": "telecom_business.docx", "score": 0.7907}, {"document_id": 1, "filename": "telecom_plans.txt", "score": 0.6993}]	\N	1
205	92	user	Is there a data cap on the unlimited plan?	2026-07-24 15:26:21	\N	\N	\N
206	92	assistant	The unlimited plan has no hard cap, but a 2 TB monthly fair-use threshold. Beyond it, speeds may be reduced during peak hours.	2026-07-24 15:26:29	\N	up	1
207	92	user	What happens if I go over 2 TB in a month?	2026-07-24 15:27:51	\N	\N	\N
208	92	assistant	Nothing is charged extra — your speed may simply be prioritised lower during peak hours (19:00-23:00) until the next billing cycle.	2026-07-24 15:27:59	\N	up	1
209	93	user	What is the wallet limit for mobile money?	2026-07-24 17:18:45	\N	\N	\N
210	93	assistant	The standard mobile money wallet is capped at 500 TND. With identity verification, the limit rises to 5,000 TND.	2026-07-24 17:18:56	\N	\N	7
211	93	user	Do I need to verify my identity?	2026-07-24 17:19:43	\N	\N	\N
212	93	assistant	Verification is optional for the basic wallet, but required for the 5,000 TND limit and for transfers to bank accounts. You can verify in any branch with your CIN.	2026-07-24 17:19:52	\N	\N	7
213	94	user	How much does the Fiber Pro plan cost?	2026-07-24 14:35:08	\N	\N	\N
214	94	assistant	The Fiber Pro plan is 89 TND per month and includes 500 Mbps download speed. Installation is free if you sign a 12-month contract.	2026-07-24 14:35:15	\N	up	7
215	94	user	Does it come with a router?	2026-07-24 14:37:13	\N	\N	\N
216	94	assistant	Yes — a WiFi 6 router is included at no extra cost and remains yours after the contract period ends.	2026-07-24 14:37:24	\N	down	7
217	95	user	What TV bundles do you offer?	2026-07-24 16:15:28	\N	\N	\N
218	95	assistant	Two bundles: Essential (60 channels, 15 TND/month) and Premium (120 channels plus sports, 35 TND/month). Both allow streaming on up to 3 devices.	2026-07-24 16:15:35	\N	\N	1
219	96	user	How does the family plan discount work?	2026-07-24 14:40:42	\N	\N	\N
220	96	assistant	Each additional line on a family plan gets 20% off its monthly fee, up to 5 lines. All lines share the plan's data allowance.	2026-07-24 14:40:47	\N	\N	3
221	97	user	What documents do I need to open a business account?	2026-07-24 11:30:49	\N	\N	\N
222	97	assistant	You'll need the company's registration certificate, tax identification, the manager's CIN, and proof of address. Opening takes 3-5 business days.	2026-07-24 11:31:01	\N	up	6
223	98	user	What interest does the savings account pay?	2026-07-24 13:35:04	\N	\N	\N
224	98	assistant	The savings account pays 5.2% annual interest, calculated daily and credited quarterly. There is no minimum balance requirement.	2026-07-24 13:35:16	\N	up	3
225	99	user	What are the fees for an international transfer?	2026-07-25 14:51:16	\N	\N	\N
226	99	assistant	International transfers cost 0.5% of the amount with a 20 TND minimum. Transfers within the SEPA zone settle in 1-2 business days.	2026-07-25 14:51:25	\N	\N	1
227	99	user	And what does a card replacement cost?	2026-07-25 14:53:42	\N	\N	\N
228	99	assistant	A replacement card is 15 TND for standard delivery, or 30 TND for express delivery within 48 hours.	2026-07-25 14:53:48	\N	\N	1
229	100	user	What compensation do I get if there is an outage?	2026-07-25 15:10:12	\N	\N	\N
230	100	assistant	If an outage lasts more than 4 consecutive hours, you receive a credit equal to one day of your subscription for each day affected, applied automatically.	2026-07-25 15:10:20	\N	\N	6
231	101	user	How do loyalty points work?	2026-07-25 09:13:45	\N	\N	\N
232	101	assistant	You earn 1 point per dinar spent on your monthly bill. Points can be redeemed for device discounts starting at 500 points, and they expire after 24 months.	2026-07-25 09:13:50	\N	\N	3
233	101	user	Do the points expire?	2026-07-25 09:15:45	\N	\N	\N
234	101	assistant	Yes, loyalty points expire 24 months after they are earned. You'll get a reminder SMS 30 days before any points lapse.	2026-07-25 09:15:55	\N	\N	3
235	102	user	bonjour	2026-07-25 19:48:59.95412	\N	\N	\N
236	102	assistant	Bonjour! Comment puis-je vous aider aujourd'hui ?	2026-07-25 19:48:59.959024	null	\N	16
237	103	user	What is the daily ATM withdrawal limit on a Visa Classic card?	2026-07-25 19:59:29.972064	\N	\N	\N
238	103	assistant	The daily ATM withdrawal limit on a Visa Classic card is 1000 dinars.	2026-07-25 19:59:29.976973	[{"document_id": 8, "filename": "biat_cards.txt", "score": 0.8263}, {"document_id": 23, "filename": "biat_branches.docx", "score": 0.7313}, {"document_id": 43, "filename": "biat_fees.txt", "score": 0.7243}, {"document_id": 22, "filename": "biat_net_banking.docx", "score": 0.7219}, {"document_id": 21, "filename": "biat_security.pdf", "score": 0.7094}]	\N	16
198	86	assistant	Good morning! How can I assist you today?	2026-07-20 08:58:20.149614	null	up	\N
239	104	user	What are your support hours?	2026-07-31 21:28:18.776231	\N	\N	\N
196	85	assistant	Good morning! How can I assist you today?	2026-07-20 08:58:14.391411	null	up	6
240	104	assistant	Our support hours are 24/7 for Fiber Pro and Fiber Max subscribers. For other plans, our support hours are 8am-8pm. You can reach us at 800-TELECOM. How can I assist you today?	2026-07-31 21:28:18.784297	[{"document_id": 3, "filename": "telecom_support.txt", "score": 0.6882}, {"document_id": 30, "filename": "telecom_complaints.docx", "score": 0.6306}, {"document_id": 31, "filename": "telecom_app.txt", "score": 0.608}, {"document_id": 28, "filename": "telecom_coverage.txt", "score": 0.5929}, {"document_id": 12, "filename": "telecom_devices.pdf", "score": 0.5921}]	\N	1
241	106	user	What is your refund policy?	2026-07-31 21:29:03.213019	\N	\N	\N
242	106	assistant	I don't have that information.	2026-07-31 21:29:03.217135	[{"document_id": 24, "filename": "topnet_billing.txt", "score": 0.5865}, {"document_id": 27, "filename": "topnet_installation.docx", "score": 0.5756}, {"document_id": 49, "filename": "topnet_fair_use.txt", "score": 0.5739}, {"document_id": 52, "filename": "topnet_moving.txt", "score": 0.5723}]	\N	1
243	107	user	What mobile plans does Telecom offer?	2026-08-02 19:56:53.327653	\N	\N	\N
244	107	assistant	Telecom offers the following mobile plans: \n\n1. Start (5 GB, 10 euros/month)\n2. Plus (30 GB, 20 euros/month)\n3. Unlimited (unlimited data, 35 euros/month)\n\nAll of these plans include unlimited calls and SMS within the country.	2026-08-02 19:56:53.333677	[{"document_id": 1, "filename": "telecom_plans.txt", "score": 0.7652}, {"document_id": 13, "filename": "telecom_business.docx", "score": 0.6942}, {"document_id": 11, "filename": "telecom_contract_terms.pdf", "score": 0.6925}, {"document_id": 4, "filename": "telecom_roaming.txt", "score": 0.691}, {"document_id": 31, "filename": "telecom_app.txt", "score": 0.6717}]	\N	1
245	118	user	ping	2026-08-02 19:57:44.0207	\N	\N	\N
246	118	assistant	Hello! How can I assist you today?	2026-08-02 19:57:44.024115	null	\N	6
247	119	user	ping	2026-08-02 19:57:44.650651	\N	\N	\N
248	119	assistant	Pong! How can I help you today?	2026-08-02 19:57:44.654224	null	\N	6
249	120	user	ping	2026-08-02 19:57:45.26101	\N	\N	\N
250	120	assistant	Hello! How can I help you today?	2026-08-02 19:57:45.264723	[{"document_id": 9, "filename": "topnet_plans.txt", "score": 0.5882}]	\N	6
251	121	user	ping	2026-08-02 19:57:45.874526	\N	\N	\N
252	121	assistant	Hello! How can I assist you today?	2026-08-02 19:57:45.876829	null	\N	6
253	122	user	ping	2026-08-02 19:57:46.521548	\N	\N	\N
254	122	assistant	Hello! How can I assist you today?	2026-08-02 19:57:46.525922	null	\N	6
255	124	user	What are your customer support hours?	2026-08-02 19:57:55.96113	\N	\N	\N
256	124	assistant	Our customer support call centres are open 24 hours a day, 7 days a week.	2026-08-02 19:57:55.965228	[{"document_id": 39, "filename": "ooredoo_customer_care.txt", "score": 0.7046}, {"document_id": 6, "filename": "ooredoo_support.txt", "score": 0.6194}, {"document_id": 17, "filename": "ooredoo_business.pdf", "score": 0.601}, {"document_id": 15, "filename": "ooredoo_billing.txt", "score": 0.5803}]	\N	3
257	126	user	What internet plans do you offer?	2026-08-02 19:58:10.539914	\N	\N	\N
258	126	assistant	We offer several internet plans. For home fibre, we have three options: Ooredoo Fibre 50 (50 Mbps, 60 dinars/month), Fibre 100 (100 Mbps, 80 dinars/month), and Fibre 200 (200 Mbps, 120 dinars/month). All of these plans include a free Wi-Fi router and unlimited data. \n\nWe also offer business fibre plans: Ooredoo Business Fibre 200 (200 Mbps, 200 dinars/month) and Business Fibre 500 (500 Mbps symmetric, 350 dinars/month), both with a fixed public IP address included and a 99.5 percent uptime commitment.	2026-08-02 19:58:10.542189	[{"document_id": 5, "filename": "ooredoo_plans.txt", "score": 0.6701}, {"document_id": 37, "filename": "ooredoo_family.txt", "score": 0.6164}, {"document_id": 40, "filename": "ooredoo_youth.txt", "score": 0.6064}, {"document_id": 17, "filename": "ooredoo_business.pdf", "score": 0.5812}]	\N	7
259	128	user	What happens if I cancel my contract early?	2026-08-02 20:03:45.411818	\N	\N	\N
260	128	assistant	If you end a contract before its agreed‑upon term finishes, you’ll generally have to pay an **early‑termination fee**.  \n\n**What the fee covers**  \n* The fee is equal to the remaining monthly payments you would have made, but it is **capped at six months’ worth of service**.  \n* If your contract includes a subsidised handset, that handset must also be **paid off in full** when you cancel early.  \n\n**When you can cancel without the early‑termination fee**  \nYou won’t be charged the fee in any of the following situations (you’ll need to provide the required proof):  \n\n1. **Moving to an address where Telecom cannot provide service** – you must submit proof of the new address.  \n2. **A documented long‑term hospital stay**.  \n3. **A price increase that exceeds the rate of inflation** – you have 30 days from the price‑change notice to terminate without penalty.  \n4. **Within the 14‑day cooling‑off period** after the contract is activated – you can cancel without any penalty.  \n\n**Other points to remember**  \n* After you give notice, the service stays active and billable until the notice period ends (30 days).  \n* Any equipment you received (router, set‑top box, etc.) must be returned undamaged within 14 days of cancellation, or you’ll be charged its full retail price.  \n\nSo, unless you fall into one of the exemption cases above, cancelling early will result in an early‑termination fee equal to the remaining monthly payments, up to a maximum of six months, plus any outstanding handset balance.	2026-08-02 20:03:45.415027	[{"document_id": 11, "filename": "telecom_contract_terms.pdf", "score": 0.7553}, {"document_id": 29, "filename": "telecom_cancellation.txt", "score": 0.7544}, {"document_id": 14, "filename": "telecom_privacy.docx", "score": 0.6469}]	\N	6
261	129	user	Do you offer any discounts for customers with disabilities?	2026-08-02 20:03:46.322024	\N	\N	\N
262	129	assistant	Yes, we offer a 20 percent discount on any mobile plan for customers with a certified disability. The certificate must be renewed every 3 years.	2026-08-02 20:03:46.324193	[{"document_id": 34, "filename": "telecom_accessibility.docx", "score": 0.689}, {"document_id": 32, "filename": "telecom_loyalty.pdf", "score": 0.5958}]	\N	3
263	133	user	How does the SLA credit work for Business Fiber?	2026-08-02 20:04:19.920068	\N	\N	\N
264	133	assistant	For Business Fiber, if the monthly uptime falls below the 99.9 percent target, the customer is credited 10 percent of the monthly fee per 0.1 percent below the target, up to a maximum of 50 percent of the monthly fee. To receive the credit, the customer must request it through the business portal within 30 days of the incident.	2026-08-02 20:04:19.924674	[{"document_id": 13, "filename": "telecom_business.docx", "score": 0.794}, {"document_id": 33, "filename": "telecom_prepaid.txt", "score": 0.6205}, {"document_id": 2, "filename": "telecom_billing.txt", "score": 0.6189}, {"document_id": 12, "filename": "telecom_devices.pdf", "score": 0.6148}]	\N	1
265	134	user	What is the process for upgrading my mobile plan in the app?	2026-08-02 20:04:20.647284	\N	\N	\N
266	134	assistant	To upgrade your mobile plan in the app, you can simply change your plan through the Telecom Mobile App. The upgrade will take effect immediately, and the difference will be prorated.	2026-08-02 20:04:20.650989	[{"document_id": 31, "filename": "telecom_app.txt", "score": 0.7109}, {"document_id": 12, "filename": "telecom_devices.pdf", "score": 0.6683}, {"document_id": 33, "filename": "telecom_prepaid.txt", "score": 0.6256}, {"document_id": 11, "filename": "telecom_contract_terms.pdf", "score": 0.6141}]	\N	1
268	135	assistant	We have three home internet options available: \n\n1. Fiber Lite, which offers 100 Mbps for 49 euros/month.\n2. Fiber Pro, which offers 500 Mbps for 79 euros/month and includes a free Wi-Fi 6 router.\n3. Fiber Max, which offers 1 Gbps for 99 euros/month and also includes a free Wi-Fi 6 router.	2026-08-02 20:04:21.317687	[{"document_id": 1, "filename": "telecom_plans.txt", "score": 0.6708}, {"document_id": 3, "filename": "telecom_support.txt", "score": 0.6313}, {"document_id": 13, "filename": "telecom_business.docx", "score": 0.5968}, {"document_id": 28, "filename": "telecom_coverage.txt", "score": 0.5912}]	\N	1
269	136	user	How does the SLA credit work for Business Fiber?	2026-08-02 22:58:55.748096	\N	\N	\N
270	136	assistant	For Business Fiber, if the monthly uptime falls below the 99.9 percent target, the customer is credited 10 percent of the monthly fee per 0.1 percent below target, up to 50 percent of the monthly fee. Credits must be requested through the business portal within 30 days of the incident.	2026-08-02 22:58:55.75243	[{"document_id": 13, "filename": "telecom_business.docx", "score": 0.794}, {"document_id": 33, "filename": "telecom_prepaid.txt", "score": 0.6205}, {"document_id": 2, "filename": "telecom_billing.txt", "score": 0.6189}, {"document_id": 12, "filename": "telecom_devices.pdf", "score": 0.6148}]	\N	1
271	137	user	How does the SLA credit work for Business Fiber?	2026-08-02 22:59:59.461158	\N	\N	\N
272	137	assistant	If the monthly uptime for Business Fiber falls below the 99.9 percent target, the customer is credited 10 percent of the monthly fee for every 0.1 percent below the target, up to a maximum of 50 percent of the monthly fee. Credits must be requested through the business portal within 30 days of the incident.	2026-08-02 22:59:59.464839	[{"document_id": 13, "filename": "telecom_business.docx", "score": 0.794}, {"document_id": 33, "filename": "telecom_prepaid.txt", "score": 0.6205}, {"document_id": 2, "filename": "telecom_billing.txt", "score": 0.6189}, {"document_id": 12, "filename": "telecom_devices.pdf", "score": 0.6148}]	\N	1
273	138	user	What mobile plans does Telecom offer?	2026-08-02 23:00:00.488483	\N	\N	\N
274	138	assistant	Telecom offers three mobile plans: \n* Start (5 GB, 10 euros/month)\n* Plus (30 GB, 20 euros/month)\n* Unlimited (unlimited data, 35 euros/month). \nAll mobile plans include unlimited calls and SMS within the country.	2026-08-02 23:00:00.492228	[{"document_id": 1, "filename": "telecom_plans.txt", "score": 0.7652}, {"document_id": 13, "filename": "telecom_business.docx", "score": 0.6942}, {"document_id": 11, "filename": "telecom_contract_terms.pdf", "score": 0.6925}, {"document_id": 4, "filename": "telecom_roaming.txt", "score": 0.691}, {"document_id": 31, "filename": "telecom_app.txt", "score": 0.6717}]	\N	1
275	139	user	What happens if I cancel my contract early?	2026-08-02 23:00:01.532434	\N	\N	\N
276	139	assistant	If you cancel your contract early, you'll incur an early termination fee equal to the remaining monthly payments, capped at 6 months of service. Additionally, if you have a subsidised handset, you'll need to pay it off in full. However, there are some exceptions where you can cancel without penalty, such as moving to an area with no coverage, a documented long-term hospital stay, or a price increase applied mid-contract.	2026-08-02 23:00:01.535446	[{"document_id": 11, "filename": "telecom_contract_terms.pdf", "score": 0.7553}, {"document_id": 29, "filename": "telecom_cancellation.txt", "score": 0.7544}, {"document_id": 14, "filename": "telecom_privacy.docx", "score": 0.6469}]	\N	1
277	140	user	What home internet options are available?	2026-08-02 23:00:02.574415	\N	\N	\N
278	140	assistant	The available home internet options are:\n* Fiber Lite (100 Mbps, 49 euros/month)\n* Fiber Pro (500 Mbps, 79 euros/month)\n* Fiber Max (1 Gbps, 99 euros/month). Note that Fiber Pro and Fiber Max include a free Wi-Fi 6 router.	2026-08-02 23:00:02.577272	[{"document_id": 1, "filename": "telecom_plans.txt", "score": 0.6708}, {"document_id": 3, "filename": "telecom_support.txt", "score": 0.6313}, {"document_id": 13, "filename": "telecom_business.docx", "score": 0.5968}, {"document_id": 28, "filename": "telecom_coverage.txt", "score": 0.5912}]	\N	1
279	141	user	Do you offer any discounts for customers with disabilities?	2026-08-02 23:00:03.199793	\N	\N	\N
280	141	assistant	Yes, we offer a 20 percent discount on any mobile plan for customers with a certified disability. The certificate must be renewed every 3 years to continue receiving the discount.	2026-08-02 23:00:03.203022	[{"document_id": 34, "filename": "telecom_accessibility.docx", "score": 0.689}, {"document_id": 32, "filename": "telecom_loyalty.pdf", "score": 0.5958}]	\N	1
281	146	user	ping	2026-08-02 23:03:20.440011	\N	\N	\N
282	146	assistant	Hello. Is there something I can help you with?	2026-08-02 23:03:20.443522	null	\N	1
283	147	user	ping	2026-08-02 23:03:21.182423	\N	\N	\N
284	147	assistant	I don't have that information. How can I help you with our Topnet Internet Plans today?	2026-08-02 23:03:21.186422	[{"document_id": 9, "filename": "topnet_plans.txt", "score": 0.5882}]	\N	1
285	148	user	ping	2026-08-02 23:03:21.751275	\N	\N	\N
286	148	assistant	Hello, it's nice to connect with you. I'm here to help with any FIAT-related questions you might have. How can I assist you today?	2026-08-02 23:03:21.753716	null	\N	1
287	149	user	ping	2026-08-02 23:03:22.247357	\N	\N	\N
288	149	assistant	I don't have any information to provide. How can I help you today?	2026-08-02 23:03:22.250629	null	\N	1
289	150	user	How do I reset my password?	2026-08-02 23:03:44.080011	\N	\N	\N
290	150	assistant	I don't have that information. I'm here to help with any questions you have, but I don't have any details on resetting passwords. Would you like me to try and find more information or assist you with something else?	2026-08-02 23:03:44.082639	null	\N	1
291	151	user	How do I reset my password?	2026-08-02 23:04:49.894313	\N	\N	\N
292	151	assistant	I don't have that information. You can contact our human support team for assistance with resetting your password. They'll be happy to help you with the process.	2026-08-02 23:04:49.897654	null	\N	1
293	152	user	Do you offer student discounts?	2026-08-02 23:04:50.667348	\N	\N	\N
294	152	assistant	I don't have that information. You can contact our human support team for more details on available discounts and promotions. They'll be happy to help you with your query.	2026-08-02 23:04:50.670243	null	\N	1
295	153	user	What is your loyalty rewards program?	2026-08-02 23:04:51.221316	\N	\N	\N
296	153	assistant	I don't have that information. You can contact our human support team for more details about our loyalty rewards program. They'll be happy to help you with any questions you may have.	2026-08-02 23:04:51.223731	null	\N	1
297	154	user	good morning what is your wourking hours	2026-08-03 09:11:16.474003	\N	\N	\N
298	154	assistant	Good morning! Our working hours are Monday to Friday, from 8 AM to 4 PM. Smaller branches may have a break from 1 PM to 2 PM during the weekdays. Saturday opening is available at selected branches in Tunis, Sfax, and Sousse, from 8 AM to noon. Please note that these times can vary by branch, so it's best to check with your specific location or use BIAT Net for up-to-date information.	2026-08-03 09:11:16.480554	[{"document_id": 22, "filename": "biat_net_banking.docx", "score": 0.6099}, {"document_id": 23, "filename": "biat_branches.docx", "score": 0.5712}]	up	16
299	154	user	okay how can i sign up for a biat account?	2026-08-03 09:36:40.280975	\N	\N	\N
300	154	assistant	To sign up for a BIAT account, you need to bring your valid national ID card or passport, proof of address dated within the last 3 months, and proof of income or employment. Here are the steps:\n\n- Visit any BIAT branch with these documents.\n- Open an account by filling out necessary forms.\n- Provide additional documentation if required for a non-resident account.\n\nFor future reference, your documents should be re-verified every 5 years or immediately upon changes in address, name, or employment.	2026-08-03 09:36:40.289229	[{"document_id": 45, "filename": "biat_kyc.txt", "score": 0.8291}, {"document_id": 22, "filename": "biat_net_banking.docx", "score": 0.8216}, {"document_id": 7, "filename": "biat_accounts.txt", "score": 0.7806}, {"document_id": 44, "filename": "biat_business_banking.docx", "score": 0.7514}, {"document_id": 23, "filename": "biat_branches.docx", "score": 0.7357}]	\N	16
301	154	user	what is the type of biat accounts i can register	2026-08-03 09:43:09.630609	\N	\N	\N
302	154	assistant	You can register for the following types of BIAT accounts:\n\n- Compte Chèque (current account)\n- Compte Epargne (savings account)\n- Compte Devise (foreign-currency account)	2026-08-03 09:43:09.636342	[{"document_id": 7, "filename": "biat_accounts.txt", "score": 0.8357}, {"document_id": 45, "filename": "biat_kyc.txt", "score": 0.8075}, {"document_id": 22, "filename": "biat_net_banking.docx", "score": 0.8012}, {"document_id": 44, "filename": "biat_business_banking.docx", "score": 0.7719}, {"document_id": 23, "filename": "biat_branches.docx", "score": 0.7718}]	\N	16
303	154	user	what is the minimum amount of moeny i need to put into an account when creating it	2026-08-03 09:53:11.418149	\N	\N	\N
304	154	assistant	When opening a BIAT bank account, the minimum deposit required is 20 dinars.	2026-08-03 09:53:11.423052	[{"document_id": 20, "filename": "biat_loans.pdf", "score": 0.6875}, {"document_id": 7, "filename": "biat_accounts.txt", "score": 0.6842}, {"document_id": 22, "filename": "biat_net_banking.docx", "score": 0.6807}, {"document_id": 45, "filename": "biat_kyc.txt", "score": 0.6797}, {"document_id": 44, "filename": "biat_business_banking.docx", "score": 0.6706}]	\N	16
\.


--
-- Data for Name: pii_rules; Type: TABLE DATA; Schema: public; Owner: orange
--

COPY public.pii_rules (id, entity_name, pattern, score, enabled, created_by, created_at, company_id) FROM stdin;
1	ACCOUNT_REFERENCE	\\bACC-\\d{6}\\b	0.85	t	\N	2026-08-03 11:39:53.833351	4
2	ACCOUNT_REFERENCE	\\bACC-\\d{6}\\b	0.85	t	\N	2026-08-03 11:39:53.833356	1
3	REF	\\bID[A-Za-z0-9]{2}02\\b	0.85	t	1	2026-08-03 11:53:58.224115	3
4	REF	\\bID[A-Za-z0-9]{2}02\\b	0.85	t	1	2026-08-03 11:53:58.224122	5
5	ORG_EMPLOYEE_ID	\\bORG-EMP-\\d{6}\\b	0.8	t	\N	2026-08-03 12:37:29.838836	\N
6	TELECOM_SUBSCRIBER_ID	\\bTC-\\d{8}\\b	0.9	t	\N	2026-08-03 12:37:29.847542	1
7	TELECOM_MSISDN	\\b(?:2|5|9)\\d{7}\\b	0.7	t	\N	2026-08-03 12:37:29.849696	1
8	OOREDOO_SIM_SERIAL	\\b89216\\d{15}\\b	0.9	t	\N	2026-08-03 12:37:29.85332	2
9	OOREDOO_CUSTOMER_REF	\\bOOR-\\d{6}\\b	0.85	t	\N	2026-08-03 12:37:29.856655	2
10	BIAT_RIB	\\b\\d{20}\\b	0.95	t	\N	2026-08-03 12:37:29.861638	3
11	BIAT_ACCOUNT_NUMBER	\\bBIAT\\d{10}\\b	0.9	t	\N	2026-08-03 12:37:29.86476	3
12	TOPNET_CONTRACT_ID	\\bTOP-\\d{7}\\b	0.8	t	\N	2026-08-03 12:37:29.868268	4
13	FIAT_VIN	\\b[A-HJ-NPR-Z0-9]{17}\\b	0.85	t	\N	2026-08-03 12:37:29.87149	5
14	FIAT_DEALER_CODE	\\bFIAT-\\d{4}\\b	0.7	t	\N	2026-08-03 12:37:29.873988	5
15	UTM_STUDENT_ID	\\b\\d{2}[A-Z]{2}\\d{4}\\b	0.8	t	\N	2026-08-03 12:37:29.878213	6
\.


--
-- Data for Name: provider_call_log; Type: TABLE DATA; Schema: public; Owner: orange
--

COPY public.provider_call_log (id, provider_id, created_at) FROM stdin;
1	3	2026-07-08 22:20:56.130868
2	3	2026-07-08 22:21:26.47686
3	2	2026-07-13 10:12:48.856491
4	1	2026-07-13 10:13:07.919133
5	2	2026-07-13 10:13:11.713985
6	3	2026-07-13 10:13:14.683001
7	4	2026-07-13 10:13:17.870241
8	1	2026-07-13 10:20:14.05804
9	1	2026-07-13 10:20:14.769324
10	1	2026-07-13 10:20:15.589883
11	1	2026-07-13 10:20:16.542329
12	1	2026-07-13 10:20:17.650717
13	2	2026-07-13 10:21:36.978239
14	2	2026-07-13 10:23:32.272747
15	3	2026-07-13 10:23:38.228977
16	1	2026-07-13 10:36:28.423965
17	1	2026-07-13 10:36:34.385095
18	1	2026-07-13 10:36:37.06406
19	1	2026-07-13 10:36:38.326525
20	2	2026-07-13 10:41:48.236215
21	2	2026-07-13 13:18:30.45628
22	1	2026-07-13 13:18:40.959968
23	1	2026-07-13 13:18:57.089748
24	1	2026-07-13 13:19:24.205431
25	5	2026-07-13 13:25:20.006688
26	2	2026-07-13 13:30:46.323749
27	6	2026-07-13 13:30:58.069331
28	6	2026-07-13 13:31:49.702414
29	6	2026-07-13 13:34:56.250113
30	6	2026-07-13 13:35:00.612806
31	6	2026-07-13 13:35:14.667902
32	2	2026-07-13 13:35:17.479337
33	6	2026-07-13 13:35:47.878624
34	7	2026-07-13 13:44:26.291777
35	7	2026-07-13 13:45:01.635204
36	7	2026-07-13 13:45:10.169053
37	4	2026-07-13 13:45:17.43425
38	7	2026-07-13 13:46:24.775472
39	6	2026-07-13 13:52:13.151061
40	6	2026-07-13 14:02:43.978696
41	1	2026-07-13 14:02:48.325182
42	3	2026-07-13 14:02:49.286494
43	7	2026-07-13 14:02:49.89721
44	5	2026-07-13 14:02:57.649044
45	4	2026-07-13 14:03:09.796355
46	6	2026-07-13 14:03:49.093937
47	2	2026-07-13 14:04:44.320793
48	4	2026-07-13 14:04:45.065456
49	5	2026-07-13 14:05:42.662869
50	3	2026-07-13 14:07:00.607065
51	6	2026-07-13 14:12:40.618214
52	1	2026-07-13 14:12:47.029025
53	3	2026-07-13 14:12:50.197263
54	7	2026-07-13 14:12:53.570095
55	6	2026-07-13 14:14:39.604768
56	1	2026-07-13 14:14:42.823014
57	3	2026-07-13 14:14:45.886533
58	7	2026-07-13 14:14:49.132061
59	6	2026-07-13 14:16:35.362592
60	1	2026-07-13 14:16:38.65961
61	3	2026-07-13 14:16:41.494363
62	7	2026-07-13 14:16:44.646881
63	6	2026-07-13 14:26:03.824132
64	1	2026-07-13 14:26:13.707422
65	3	2026-07-13 14:26:17.33635
66	7	2026-07-13 14:26:20.866393
67	6	2026-07-13 14:28:58.608256
68	1	2026-07-13 14:29:01.708008
69	3	2026-07-13 14:29:04.831159
70	7	2026-07-13 14:29:08.34605
71	6	2026-07-13 14:29:19.770196
72	1	2026-07-13 14:29:22.809899
73	3	2026-07-13 14:29:27.514102
74	7	2026-07-13 14:29:30.919315
75	6	2026-07-13 14:31:14.291693
76	1	2026-07-13 14:31:17.275897
77	3	2026-07-13 14:31:20.435521
78	7	2026-07-13 14:31:23.523325
79	6	2026-07-13 14:33:33.59788
80	1	2026-07-13 14:33:36.811613
81	3	2026-07-13 14:33:39.944889
82	7	2026-07-13 14:33:43.209562
83	1	2026-07-13 16:41:51.115647
84	2	2026-07-13 16:41:55.227325
85	3	2026-07-13 16:41:55.889319
86	4	2026-07-13 16:41:56.505823
87	5	2026-07-13 16:41:57.319502
88	6	2026-07-13 16:41:57.6442
89	7	2026-07-13 16:41:59.553839
90	8	2026-07-13 19:29:01.231578
91	1	2026-07-13 19:39:52.409702
92	9	2026-07-13 19:43:47.139423
93	6	2026-07-13 19:47:12.380282
94	6	2026-07-13 19:47:25.618424
95	6	2026-07-13 19:47:33.564881
96	8	2026-07-13 19:47:35.895719
97	9	2026-07-13 19:47:40.431235
98	3	2026-07-13 19:47:54.390855
99	6	2026-07-13 19:55:35.034596
100	6	2026-07-13 19:55:44.941045
101	6	2026-07-13 19:58:52.333332
102	6	2026-07-13 19:59:03.610484
103	6	2026-07-13 19:59:45.459104
104	9	2026-07-13 21:01:59.351655
105	4	2026-07-13 21:02:05.132217
106	8	2026-07-13 21:02:05.470629
107	5	2026-07-13 21:02:05.787357
137	6	2026-07-14 09:04:07.788102
138	2	2026-07-14 09:04:15.806469
139	6	2026-07-14 09:42:18.952443
140	1	2026-07-14 09:42:27.659382
141	3	2026-07-14 09:42:30.890906
142	7	2026-07-14 09:42:36.761552
143	6	2026-07-14 10:05:06.00411
144	7	2026-07-14 10:05:26.163863
145	2	2026-07-14 10:30:32.419751
153	5	2026-07-14 12:51:37.059976
154	4	2026-07-14 12:51:43.571004
155	2	2026-07-14 12:51:46.304971
160	6	2026-07-16 09:04:19.134089
161	6	2026-07-16 09:05:19.139176
162	1	2026-07-16 09:05:25.073702
163	6	2026-07-16 09:05:32.333182
164	6	2026-07-16 09:08:39.98679
165	6	2026-07-16 09:08:52.346751
166	6	2026-07-16 09:40:29.523236
167	6	2026-07-20 08:58:06.59985
168	6	2026-07-20 08:58:06.629065
170	6	2026-07-23 21:15:42.128573
171	1	2026-07-23 21:15:47.13657
172	6	2026-07-23 21:16:01.653377
173	2	2026-07-23 21:16:02.072454
174	6	2026-07-23 21:16:14.561042
175	2	2026-07-23 21:16:15.130714
176	6	2026-07-23 21:16:27.814283
177	1	2026-07-23 21:16:29.238271
178	6	2026-07-23 21:16:44.222656
179	1	2026-07-23 21:16:44.640494
180	2	2026-07-25 19:26:49.482075
181	16	2026-07-25 19:35:21.946832
182	16	2026-07-25 19:39:38.786372
183	16	2026-07-25 19:48:49.012271
184	16	2026-07-25 19:48:58.820482
185	16	2026-07-25 19:59:15.829444
187	17	2026-07-25 20:03:42.675395
188	17	2026-07-25 20:07:18.559568
189	1	2026-07-31 21:28:09.951945
190	1	2026-07-31 21:29:02.962251
191	1	2026-07-31 21:30:00.700636
192	1	2026-07-31 21:31:38.222171
193	1	2026-07-31 21:32:39.000769
194	1	2026-07-31 21:32:42.170955
195	1	2026-07-31 21:32:42.199811
196	1	2026-07-31 21:32:42.226701
197	1	2026-07-31 21:32:42.229043
198	1	2026-07-31 21:32:42.231781
199	1	2026-07-31 21:32:42.241819
200	1	2026-07-31 21:32:42.269491
201	1	2026-07-31 21:32:42.296965
202	1	2026-07-31 21:32:42.29808
203	1	2026-07-31 21:32:42.305152
204	1	2026-07-31 21:33:36.102971
205	1	2026-07-31 21:33:39.758317
206	1	2026-07-31 21:33:39.769501
207	1	2026-07-31 21:33:39.777991
208	1	2026-07-31 21:33:39.798426
209	1	2026-07-31 21:33:39.837073
210	1	2026-07-31 21:33:39.84062
211	1	2026-07-31 21:33:39.841394
212	1	2026-07-31 21:33:39.845315
213	1	2026-07-31 21:33:39.848471
214	1	2026-07-31 21:33:39.875474
215	1	2026-08-02 19:56:46.970796
216	6	2026-08-02 19:57:43.182828
217	6	2026-08-02 19:57:44.3286
218	6	2026-08-02 19:57:44.939976
219	6	2026-08-02 19:57:45.568753
220	6	2026-08-02 19:57:46.167428
221	6	2026-08-02 19:57:54.340046
222	3	2026-08-02 19:57:55.026469
223	2	2026-08-02 19:57:56.290788
224	7	2026-08-02 19:57:57.30657
225	6	2026-08-02 20:03:44.742632
226	3	2026-08-02 20:03:45.749858
227	2	2026-08-02 20:03:46.607512
228	7	2026-08-02 20:03:47.671927
229	4	2026-08-02 20:04:03.34445
230	1	2026-08-02 20:04:19.395282
231	1	2026-08-02 20:04:20.248858
232	1	2026-08-02 20:04:20.95596
233	1	2026-08-02 22:58:50.176528
234	1	2026-08-02 22:59:54.940693
235	1	2026-08-02 22:59:59.961685
236	1	2026-08-02 23:00:00.804224
237	1	2026-08-02 23:00:01.828137
238	1	2026-08-02 23:00:02.913564
239	1	2026-08-02 23:03:15.73302
240	1	2026-08-02 23:03:20.97181
241	1	2026-08-02 23:03:21.491419
242	1	2026-08-02 23:03:22.038552
243	1	2026-08-02 23:03:43.677202
244	1	2026-08-02 23:04:45.773026
245	1	2026-08-02 23:04:50.402016
246	1	2026-08-02 23:04:50.978459
247	6	2026-08-03 08:29:35.689174
248	6	2026-08-03 08:29:51.521204
249	6	2026-08-03 08:29:53.701463
250	6	2026-08-03 08:29:53.738867
251	6	2026-08-03 08:29:53.746003
252	6	2026-08-03 08:29:53.757974
253	6	2026-08-03 08:29:53.760276
254	6	2026-08-03 08:29:53.76491
255	6	2026-08-03 08:29:53.775767
256	6	2026-08-03 08:29:53.776596
257	6	2026-08-03 08:29:53.778018
258	6	2026-08-03 08:29:53.781555
259	6	2026-08-03 08:29:53.79864
260	6	2026-08-03 08:29:53.858855
261	6	2026-08-03 08:29:53.953142
262	6	2026-08-03 08:29:54.062534
263	6	2026-08-03 08:29:54.157037
264	6	2026-08-03 08:29:54.270268
265	6	2026-08-03 08:29:54.363774
266	6	2026-08-03 08:29:54.471389
267	6	2026-08-03 08:29:54.561128
268	6	2026-08-03 08:29:54.663628
269	6	2026-08-03 08:29:54.760837
270	6	2026-08-03 08:29:54.975759
271	6	2026-08-03 08:29:55.156241
272	6	2026-08-03 08:29:55.355646
273	6	2026-08-03 08:29:55.568546
274	6	2026-08-03 08:29:55.764937
275	6	2026-08-03 08:29:55.912181
276	6	2026-08-03 08:29:56.160216
277	6	2026-08-03 08:59:46.328125
278	6	2026-08-03 09:07:44.209677
279	6	2026-08-03 09:07:46.440327
280	6	2026-08-03 09:07:46.44932
281	6	2026-08-03 09:07:46.460322
282	6	2026-08-03 09:07:47.338889
283	6	2026-08-03 09:07:47.411108
284	6	2026-08-03 09:07:47.712024
285	6	2026-08-03 09:07:49.147239
286	16	2026-08-03 09:11:00.321938
287	6	2026-08-03 09:14:00.583157
288	6	2026-08-03 09:14:02.857753
289	6	2026-08-03 09:14:03.606971
290	6	2026-08-03 09:24:10.240436
291	6	2026-08-03 09:24:45.807432
292	6	2026-08-03 09:24:51.345862
293	6	2026-08-03 09:24:52.824535
294	6	2026-08-03 09:24:54.543652
295	6	2026-08-03 09:24:56.057834
296	6	2026-08-03 09:24:57.65658
297	6	2026-08-03 09:25:43.913371
298	6	2026-08-03 09:25:51.994384
299	6	2026-08-03 09:25:55.968202
300	6	2026-08-03 09:26:00.102269
301	6	2026-08-03 09:26:04.307388
302	6	2026-08-03 09:26:08.332685
303	6	2026-08-03 09:26:11.095835
304	6	2026-08-03 09:26:13.816888
305	6	2026-08-03 09:26:17.91323
306	6	2026-08-03 09:26:20.646424
307	6	2026-08-03 09:26:23.403911
308	6	2026-08-03 09:26:26.145104
309	6	2026-08-03 09:26:30.385362
310	6	2026-08-03 09:26:33.113499
311	6	2026-08-03 09:26:35.887901
312	6	2026-08-03 09:26:38.612906
313	6	2026-08-03 09:26:42.915571
314	6	2026-08-03 09:26:45.641497
315	6	2026-08-03 09:26:48.402211
316	6	2026-08-03 09:26:51.145256
317	6	2026-08-03 09:26:55.474261
318	6	2026-08-03 09:26:58.190522
319	6	2026-08-03 09:27:01.033776
320	6	2026-08-03 09:27:03.803012
321	6	2026-08-03 09:27:07.964304
322	6	2026-08-03 09:27:10.733793
323	6	2026-08-03 09:27:13.483416
324	6	2026-08-03 09:27:16.221671
325	6	2026-08-03 09:27:20.242366
326	6	2026-08-03 09:27:22.988439
327	16	2026-08-03 09:31:26.808997
328	16	2026-08-03 09:31:46.760686
329	16	2026-08-03 09:31:53.33068
330	16	2026-08-03 09:32:02.500039
331	16	2026-08-03 09:32:12.30743
332	16	2026-08-03 09:32:19.867761
333	16	2026-08-03 09:32:28.113281
334	16	2026-08-03 09:32:39.069027
335	16	2026-08-03 09:32:47.297317
336	16	2026-08-03 09:32:52.799194
337	16	2026-08-03 09:32:58.555504
338	16	2026-08-03 09:33:08.086629
339	16	2026-08-03 09:33:16.669473
340	16	2026-08-03 09:33:26.043898
341	16	2026-08-03 09:33:34.842804
342	16	2026-08-03 09:33:42.405071
343	16	2026-08-03 09:33:48.296713
344	16	2026-08-03 09:33:57.388066
345	16	2026-08-03 09:34:06.204607
346	16	2026-08-03 09:34:15.056665
347	16	2026-08-03 09:34:23.33615
348	16	2026-08-03 09:34:30.359647
349	16	2026-08-03 09:34:38.009407
350	16	2026-08-03 09:34:47.393021
351	16	2026-08-03 09:34:55.099265
352	16	2026-08-03 09:35:03.640274
353	16	2026-08-03 09:35:13.479756
354	16	2026-08-03 09:35:22.034365
355	16	2026-08-03 09:35:31.577699
356	16	2026-08-03 09:35:40.232046
357	16	2026-08-03 09:36:27.727551
358	16	2026-08-03 09:42:54.586214
359	16	2026-08-03 09:52:55.129774
360	16	2026-08-03 10:00:17.667906
361	16	2026-08-03 10:00:38.278818
362	16	2026-08-03 10:00:43.92555
363	16	2026-08-03 10:00:50.714506
364	16	2026-08-03 10:00:57.608194
365	16	2026-08-03 10:01:06.752164
366	16	2026-08-03 10:01:15.637876
367	16	2026-08-03 10:01:22.943998
368	16	2026-08-03 10:01:30.227252
369	16	2026-08-03 10:01:38.179953
370	16	2026-08-03 10:01:43.917631
371	16	2026-08-03 10:01:51.62065
372	16	2026-08-03 10:01:59.772957
373	16	2026-08-03 10:02:05.665362
374	16	2026-08-03 10:02:11.554981
375	16	2026-08-03 10:02:18.897173
376	16	2026-08-03 10:02:26.31502
377	16	2026-08-03 10:02:31.987453
378	16	2026-08-03 10:02:37.444816
379	16	2026-08-03 10:02:45.056348
380	16	2026-08-03 10:02:53.163332
381	16	2026-08-03 10:03:01.45523
382	16	2026-08-03 10:03:07.166273
383	16	2026-08-03 10:03:12.747269
384	16	2026-08-03 10:03:19.844758
385	16	2026-08-03 10:03:25.443094
386	16	2026-08-03 10:03:33.956534
387	16	2026-08-03 10:03:39.610243
388	16	2026-08-03 10:03:45.091834
389	16	2026-08-03 10:03:50.726896
\.


--
-- Data for Name: staged_chunks; Type: TABLE DATA; Schema: public; Owner: orange
--

COPY public.staged_chunks (id, company_id, conversation_id, document_id, text, category, created_at, expires_at) FROM stdin;
\.


--
-- Data for Name: token_requests; Type: TABLE DATA; Schema: public; Owner: orange
--

COPY public.token_requests (id, requester_id, company_id, scope, requested_limit, reason, status, decision_reason, reviewed_by, reviewed_at, created_at) FROM stdin;
3	2	1	company	500	We have a big project comming up	approved	\N	1	2026-07-30 17:07:36.068131	2026-07-30 17:07:22.209011
4	2	1	company	400	We have a big project comming up	approved	\N	1	2026-07-30 17:08:27.52515	2026-07-30 17:08:20.792371
\.


--
-- Data for Name: token_usage; Type: TABLE DATA; Schema: public; Owner: orange
--

COPY public.token_usage (id, company_id, user_id, provider_id, conversation_id, prompt_tokens, completion_tokens, total_tokens, created_at, reasoning_tokens) FROM stdin;
1	1	3	3	1	569	26	595	2026-07-08 22:21:01.941024	\N
2	1	3	3	2	437	12	449	2026-07-08 22:21:31.95243	\N
3	1	3	1	4	734	141	875	2026-07-13 10:13:09.43161	\N
4	1	3	3	6	756	53	809	2026-07-13 10:13:15.590428	\N
5	3	1	1	8	554	39	593	2026-07-13 10:20:14.451413	\N
6	2	1	1	9	293	28	321	2026-07-13 10:20:15.318919	\N
7	1	1	1	10	734	114	848	2026-07-13 10:20:16.251225	\N
8	4	1	1	11	159	18	177	2026-07-13 10:20:16.757983	\N
9	1	3	1	12	734	114	848	2026-07-13 10:20:18.74835	\N
10	3	1	3	15	79	11	90	2026-07-13 10:23:38.655835	\N
245	4	16	1	68	429	47	476	2026-07-12 15:26:29	0
12	1	1	1	17	734	114	848	2026-07-13 10:36:36.764954	\N
13	2	1	1	18	293	29	322	2026-07-13 10:36:37.462755	\N
246	4	16	1	68	450	57	507	2026-07-12 15:27:58	0
247	2	7	1	69	364	38	402	2026-07-12 13:08:17	0
248	2	7	1	69	474	58	532	2026-07-12 13:10:51	0
249	1	3	6	70	528	35	563	2026-07-12 08:41:49	0
15	3	1	1	8	107	8	115	2026-07-13 13:18:42.006628	\N
16	3	1	1	8	105	29	134	2026-07-13 13:18:57.687027	\N
17	3	1	1	8	828	103	931	2026-07-13 13:19:25.823915	\N
18	1	3	6	24	767	185	952	2026-07-13 13:35:01.007211	\N
19	1	3	6	25	767	193	960	2026-07-13 13:35:18.651553	\N
20	3	1	6	27	135	137	272	2026-07-13 13:35:48.889868	\N
21	3	1	7	28	69	21	90	2026-07-13 13:45:43.630945	\N
250	1	3	6	70	384	48	432	2026-07-12 08:42:40	0
23	1	3	7	31	705	55	760	2026-07-13 13:47:54.816306	\N
24	1	3	6	32	767	228	995	2026-07-13 13:52:17.389695	\N
251	4	16	7	71	286	60	346	2026-07-14 14:35:15	0
25	3	1	6	28	133	110	243	2026-07-13 14:03:49.88885	\N
26	3	1	3	34	78	10	88	2026-07-13 14:07:04.175299	\N
27	1	4	6	35	742	180	922	2026-07-13 14:12:44.483698	\N
28	1	4	1	35	749	18	767	2026-07-13 14:12:47.549406	\N
29	1	4	3	36	738	50	788	2026-07-13 14:12:51.030173	\N
30	1	4	7	36	731	42	773	2026-07-13 14:14:36.953644	\N
31	1	4	6	37	771	73	844	2026-07-13 14:14:40.282393	\N
32	1	4	1	37	758	66	824	2026-07-13 14:14:43.22986	\N
33	1	4	3	38	736	54	790	2026-07-13 14:14:46.585866	\N
34	1	4	7	38	711	224	935	2026-07-13 14:16:32.527887	\N
35	1	4	6	39	783	52	835	2026-07-13 14:16:35.978008	\N
36	2	6	1	40	687	14	701	2026-07-13 14:16:38.93902	\N
37	2	6	3	40	809	34	843	2026-07-13 14:16:42.098378	\N
38	1	4	6	41	742	272	1014	2026-07-13 14:26:11.144036	\N
39	1	4	1	41	749	18	767	2026-07-13 14:26:14.640881	\N
40	1	4	3	42	738	50	788	2026-07-13 14:26:18.3125	\N
41	2	6	7	40	422	92	514	2026-07-13 14:28:55.264189	\N
42	2	7	6	43	820	138	958	2026-07-13 14:28:59.078673	\N
43	2	7	1	43	725	32	757	2026-07-13 14:29:02.07757	\N
44	2	6	3	44	766	21	787	2026-07-13 14:29:05.797735	\N
45	1	4	7	42	731	44	775	2026-07-13 14:29:17.085695	\N
46	1	4	6	45	771	62	833	2026-07-13 14:29:20.233539	\N
47	1	4	1	45	758	57	815	2026-07-13 14:29:24.775668	\N
48	2	6	3	46	715	19	734	2026-07-13 14:29:28.340064	\N
49	2	6	7	44	241	13	254	2026-07-13 14:31:11.601462	\N
50	2	7	6	47	262	290	552	2026-07-13 14:31:14.72824	\N
51	2	7	1	47	644	37	681	2026-07-13 14:31:17.678575	\N
52	2	6	3	48	879	23	902	2026-07-13 14:31:20.94378	\N
53	2	6	7	48	567	182	749	2026-07-13 14:33:30.858113	\N
54	2	7	6	49	635	361	996	2026-07-13 14:33:34.095819	\N
55	2	6	1	50	225	52	277	2026-07-13 14:33:37.234628	\N
56	3	9	3	51	854	38	892	2026-07-13 14:33:40.663596	\N
57	1	13	1	53	751	132	883	2026-07-13 19:39:57.035008	0
58	3	10	6	55	817	361	1178	2026-07-13 19:47:13.528153	161
59	3	10	6	55	139	72	211	2026-07-13 19:47:25.928029	53
60	3	10	6	55	134	75	209	2026-07-13 19:47:33.908889	52
61	3	10	3	56	79	11	90	2026-07-13 19:47:55.041954	0
62	1	13	6	57	133	77	210	2026-07-13 19:55:35.413469	53
63	1	13	6	57	450	118	568	2026-07-13 19:55:45.87496	96
64	1	13	6	58	453	71	524	2026-07-13 19:58:52.725309	54
65	1	13	6	58	132	96	228	2026-07-13 19:59:04.092702	74
66	1	13	6	59	156	76	232	2026-07-13 19:59:45.751547	59
67	3	9	6	62	134	194	328	2026-07-14 10:05:10.751825	172
68	3	9	7	63	97	11	108	2026-07-14 10:05:41.086647	0
252	2	14	8	72	481	34	515	2026-07-14 09:25:05	0
253	3	10	1	73	276	27	303	2026-07-14 16:15:35	0
70	3	1	6	65	134	176	310	2026-07-16 09:04:20.920725	154
71	3	1	6	66	134	148	282	2026-07-16 09:05:19.574288	131
72	3	1	1	66	97	11	108	2026-07-16 09:05:25.669299	0
73	3	1	6	66	133	135	268	2026-07-16 09:05:33.82958	118
74	3	1	6	67	177	58	235	2026-07-16 09:08:44.020012	38
75	3	1	6	67	836	508	1344	2026-07-16 09:09:00.785345	64
254	3	10	3	74	322	33	355	2026-07-14 10:20:45	0
255	3	15	6	75	433	47	480	2026-07-14 12:13:42	0
256	3	15	6	75	448	48	496	2026-07-14 12:14:26	0
257	1	3	2	76	476	30	506	2026-07-14 09:19:01	0
258	1	4	3	77	395	44	439	2026-07-15 14:47:22	0
259	1	4	3	77	365	41	406	2026-07-15 14:49:28	0
260	1	4	4	78	480	34	514	2026-07-15 11:29:12	0
261	2	14	6	79	506	40	546	2026-07-15 11:12:48	0
262	4	12	1	80	319	36	355	2026-07-15 16:57:12	0
263	4	16	6	81	426	56	482	2026-07-15 16:23:36	0
264	4	16	6	81	322	53	375	2026-07-15 16:25:30	0
265	2	7	7	82	322	44	366	2026-07-15 09:34:45	0
266	2	7	7	82	413	41	454	2026-07-15 09:35:37	0
267	2	1	6	83	745	132	877	2026-07-16 09:40:33.63144	70
268	3	1	6	85	179	74	253	2026-07-20 08:58:14.373	54
270	1	3	6	\N	144	90	234	2026-07-23 21:15:47.061826	64
271	1	3	1	87	635	117	752	2026-07-23 21:15:47.964452	0
272	1	3	6	\N	144	108	252	2026-07-23 21:16:02.016362	84
273	1	3	6	\N	144	108	252	2026-07-23 21:16:15.078876	84
274	1	3	6	\N	144	108	252	2026-07-23 21:16:29.187128	84
275	1	3	1	90	574	125	699	2026-07-23 21:16:29.853082	0
276	1	3	6	\N	142	79	221	2026-07-23 21:16:44.589242	56
277	1	3	1	91	633	104	737	2026-07-23 21:16:45.30988	0
278	4	16	1	92	450	56	506	2026-07-24 15:26:29	0
279	4	16	1	92	507	33	540	2026-07-24 15:27:59	0
280	2	7	7	93	371	18	389	2026-07-24 17:18:56	0
281	2	7	7	93	308	59	367	2026-07-24 17:19:52	0
282	1	3	7	94	274	27	301	2026-07-24 14:35:15	0
283	1	3	7	94	478	28	506	2026-07-24 14:37:24	0
284	4	16	1	95	278	49	327	2026-07-24 16:15:35	0
285	2	14	3	96	357	46	403	2026-07-24 14:40:47	0
286	3	10	6	97	310	37	347	2026-07-24 11:31:01	0
287	3	10	3	98	416	35	451	2026-07-24 13:35:16	0
288	3	15	1	99	372	44	416	2026-07-25 14:51:25	0
289	3	15	1	99	496	40	536	2026-07-25 14:53:48	0
290	1	3	6	100	435	32	467	2026-07-25 15:10:20	0
291	1	4	3	101	275	54	329	2026-07-25 09:13:50	0
292	1	4	3	101	310	53	363	2026-07-25 09:15:55	0
293	3	1	16	\N	69	2	71	2026-07-25 19:48:58.452761	0
294	3	1	16	102	160	12	172	2026-07-25 19:48:59.947602	0
295	3	9	16	103	864	20	884	2026-07-25 19:59:29.966328	0
269	3	1	\N	86	123	11	134	2026-07-20 08:58:20.139075	0
296	1	3	1	104	822	51	873	2026-07-31 21:28:18.764311	0
297	4	12	1	106	557	8	565	2026-07-31 21:29:03.206211	0
298	1	13	1	107	802	60	862	2026-08-02 19:56:53.318867	0
299	2	1	6	118	177	88	265	2026-08-02 19:57:44.013257	69
300	3	1	6	119	176	114	290	2026-08-02 19:57:44.642734	94
301	4	1	6	120	239	88	327	2026-08-02 19:57:45.255344	69
302	5	1	6	121	176	112	288	2026-08-02 19:57:45.868871	93
303	6	1	6	122	176	102	278	2026-08-02 19:57:46.513874	83
304	2	1	3	124	890	21	911	2026-08-02 19:57:55.955475	0
305	2	1	7	126	828	137	965	2026-08-02 19:58:10.528512	0
306	1	1	6	128	825	560	1385	2026-08-02 20:03:45.406359	209
307	1	1	3	129	393	32	425	2026-08-02 20:03:46.315626	0
308	1	1	1	133	858	75	933	2026-08-02 20:04:19.91225	0
309	1	1	1	134	773	38	811	2026-08-02 20:04:20.641219	0
310	1	1	1	135	699	78	777	2026-08-02 20:04:21.310069	0
311	1	1	1	136	890	65	955	2026-08-02 22:58:55.739833	0
312	1	1	1	137	890	69	959	2026-08-02 22:59:59.451785	0
313	1	1	1	138	834	56	890	2026-08-02 23:00:00.482473	0
314	1	1	1	139	829	89	918	2026-08-02 23:00:01.524959	0
315	1	1	1	140	731	61	792	2026-08-02 23:00:02.567845	0
316	1	1	1	141	423	36	459	2026-08-02 23:00:03.195112	0
317	3	1	1	146	171	12	183	2026-08-02 23:03:20.432181	0
318	4	1	1	147	235	21	256	2026-08-02 23:03:21.175792	0
319	5	1	1	148	171	33	204	2026-08-02 23:03:21.744899	0
320	6	1	1	149	171	17	188	2026-08-02 23:03:22.241566	0
321	3	1	1	150	177	47	224	2026-08-02 23:03:44.075161	0
322	3	1	1	151	213	33	246	2026-08-02 23:04:49.887113	0
323	3	1	1	152	212	35	247	2026-08-02 23:04:50.661003	0
324	3	1	1	153	213	38	251	2026-08-02 23:04:51.215327	0
325	3	1	16	154	467	95	562	2026-08-03 09:11:16.464973	0
326	3	1	16	154	750	105	855	2026-08-03 09:36:40.274492	0
327	3	1	16	154	749	45	794	2026-08-03 09:43:09.622443	0
328	3	1	16	154	903	20	923	2026-08-03 09:53:11.411371	0
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: orange
--

COPY public.users (id, email, password_hash, role, company_id, daily_token_limit, created_at) FROM stdin;
1	admin@orange.com	scrypt:32768:8:1$7ptkJyvvjX1N5euU$21dffcb8c5cc983fd0e57a067e2ac8986ed08f390c67ac18abb939667d3788dc0ce74fbec4f76bba58bda63e0e82a9092ca6b08b199c4bf8d6385de0472af7fd	super_admin	\N	\N	2026-07-08 11:28:06.171269
23	user12@utm.com	scrypt:32768:8:1$YONRsfzjkFzhz4dh$91281c902e14d67f23ec6677412357c6591b38adbffb30a789095e27dc36d707ff4fa74b7bea2361ea909da8beb4f0d8e19f1d67fbb2758f39bb295a324874dc	customer	6	\N	2026-07-14 09:43:39.338227
24	admin@globalnet.com	scrypt:32768:8:1$329gT9Gem1ZSAWqp$a612e412d1674b94931005dd268d894aee61d5457d537839ba0f376f625dc0d048b7e7dde5cce3943c0a4a489f570661a412c9585170a8791e21f18943310c36	company_admin	8	\N	2026-07-14 12:52:49.52257
25	sami@globalnet.com	scrypt:32768:8:1$XE0Zmq5JMSERWuVl$2b6b56f579f5dd284b569ad262c7363d7244d9df1084f5024c87b29cc655cbcd713e133a14698b5d45aa00c80dde9cf7e4ea0e3793de8b38ac56d9d097f5849c	customer	8	\N	2026-07-14 12:57:50.432244
13	user@telecom.com	scrypt:32768:8:1$puA8A5OHwApeuVxZ$952de23cdc554de2e2b1b1fb585c9a355ddc1d7efe6a08e8757d4630c8efc98431c93ed255658b5de0696ee34a9c14d1f6d2535e2bdc854179dd2e4a2eab1c66	customer	1	20000	2026-07-13 19:15:38.460767
26	admin@test.com	scrypt:32768:8:1$5V1RCERXhrsgB5D7$1ecdf36bfcf2d3a315fc8f4b6b93ff69ef2c88be746d53c11e6c4b7d8c7940b806c9c84497ca384fa65ebfddd171ee66ccc61daf006a44db218bb384c0933814	company_admin	9	\N	2026-07-25 19:31:49.048718
27	admin@oxford.us	scrypt:32768:8:1$bpEIcfddToRUyN25$d444ce6fe7399a724dad98ca9ba2c0258faf82f5e468a7e05359f9150609503d205c80020de800bcf3f039d6885bc6b5642e044df1d97f71fca84b9de28d7c68	company_admin	10	\N	2026-07-25 19:31:49.164246
28	sami@biat.com.tn	scrypt:32768:8:1$JicBppIzmS6ma36g$1d8c7fed8435a33a09c1c1a3cc82c9e78bc8e995762a42e30b4a6b4f6f937c502ded9766f65568da1be3572c7feab52b3f2f99913ebf8dc3a2d128d677593868	customer	3	500	2026-07-25 19:52:53.930471
2	admin@telecom.com	scrypt:32768:8:1$6tPllo5uDS4RLoV4$70736949cfc4ac133f30e81f3711de5edf422eece420cd117a69ccf1f29ed1b3182198a672b45feabd775e0b21ab56ade5043674e8211e945ca0cdc5ce457cd7	company_admin	1	40000	2026-07-08 11:28:06.271842
3	alice@telecom.com	scrypt:32768:8:1$PmeYTXTkYBDQByOv$d7cef214b3d5c716515c595f956f313dc8c7da81ed7bf0403024b3f42c619aff5eff8c6a37d2b9dc7e728481ff123c8efddd9562c191a26525a39bc3c050c705	customer	1	20000	2026-07-08 11:28:06.374937
4	sami@telecom.com	scrypt:32768:8:1$Ct0gICwv29wQd7kp$255d9b06ff10a074e471d1d91150ef4bf4bf65e4ceac933c2e96634f33e7ce9cd3ceb4f4b98888132fc50fc580e306afd2207efc72d7665b17bd2527e2dfea57	customer	1	20000	2026-07-08 11:28:06.474652
5	admin@ooredoo.tn	scrypt:32768:8:1$arvO7DYuZgM9PDWN$61deea2cf8427a2e7fe561732a868bca3f3e9843eaecb930bf854f3dfca69032dc2112e3ba068d214789c8042faefd0a00914b50a346ee66ac97aea88ed68a7b	company_admin	2	30000	2026-07-08 11:28:06.574786
14	user@ooredoo.tn	scrypt:32768:8:1$JlNKZmtGWDlTcI6k$92dda316bf4159e15549b0d3fcd9de2e6b33bf1306acabe2b1e1caa3644c66177c8e58bdaa3fc743db27e6ce3d228f70a59139804aadca5c251842af6e18d016	customer	2	15000	2026-07-13 19:15:38.580428
6	leila@ooredoo.tn	scrypt:32768:8:1$YaG6ZoiRHFXh4rMF$6d6f9f9ff3daf464324e3efd300777a6648dbe7b4f605b18695d3b7642e459f82ba1e81188c5753fdb676c835a60819f1d02438ed3792b9959106ad4eefd6f7b	customer	2	15000	2026-07-08 11:28:06.678287
7	karim@ooredoo.tn	scrypt:32768:8:1$IfimHivcOZDhGVxW$9ac92c60c84c130e8880e016f962831d0c92648dd5ee8517f17bf21e0ea70da80a56e5b56811422c94dd8ab8956e9c7d76b8928e50805bad7f179bf4c91cbe6f	customer	2	15000	2026-07-08 11:28:06.779945
8	admin@biat.com.tn	scrypt:32768:8:1$WXNduYxe0OJRbakg$8f5b1ef2dc150076962e8f544a15b363ec969c4c8f8de5fdce9f5a5a83bcdb209527db107a2b7ee07ec76cbffb6c0bcdc5c70dfd3ebb64f32a09fb9451b9ac7c	company_admin	3	20000	2026-07-08 11:28:06.878855
15	user@biat.com.tn	scrypt:32768:8:1$mKGrdhHpljVUAxZK$d05589ec155dc9358bfc9d01fcd6be7fd849d9e6060b7a6b04402d4ce21d81e4e0e58637b31f7be9606fd170d4db72a6c8edc6ecd2cd54adc2d5e3c17d15eb72	customer	3	10000	2026-07-13 19:15:38.690671
9	nadia@biat.com.tn	scrypt:32768:8:1$xyjWe2QIuVEwDokn$3ace5d276fddb469a02522af3aa7ea52ca5a8f3ed2e47af6dc29921ed18c901475af3ba287437affb941b1096332089ddfdc50ee61896f9f89de08dbd37f965f	customer	3	10000	2026-07-08 11:28:06.980424
10	mehdi@biat.com.tn	scrypt:32768:8:1$bVEexq0OpuX9PEsV$83ac3f1d42a1339f7dbc1488ca85886e9382ed9468f384d587a7183b572f063d1b6f285ac667258ac5f9ab616bf8e314e8d6e9dc0da7be1312425b0b3fd3ca6d	customer	3	10000	2026-07-08 11:28:07.081945
11	admin@topnet.com	scrypt:32768:8:1$uhX2irSgRwFEqw2T$a46ba0c5cb45576ea186c2874431318db8137b8c87cc8394993588aa2e4fa9f7f3e6e166a1246160e445a030bc5b6f9d2da3a3afc2ad7ca57e00502bafc92a79	company_admin	4	10000	2026-07-08 11:28:07.203931
16	user@topnet.com	scrypt:32768:8:1$e9vwM0zN8JbWpbLK$3f7e7d9c6082f3ad4ae438adc4a00842155a8e6d99b4a0b6412839c9796c47e9d978641f0fb66a280329704d3841432ecadb3cb72a8716c1f9ea08f8aead849f	customer	4	5000	2026-07-13 19:15:38.797781
12	bob@topnet.com	scrypt:32768:8:1$9pniMFmT3BDp5czm$7e7e528b8607113446212516bdd34dc52caec843b5552efcfe9ccfa559d34112a75a5173ad6ecc4c8400f709b092596b2b7ec05b9c648043c03c6968b36d375b	customer	4	5000	2026-07-08 11:28:07.329022
17	admin@fiat.com	scrypt:32768:8:1$PQ5YCUhB25o2MEbi$a108a4d5ebe7fca7bf0a54cf4f2d73f312c948852e0749569f0b051bdc1cd3fa28b63ac247ec146741c8422f7f154a16ef593d932cb6f2789de72a94ea4826ec	company_admin	5	4000	2026-07-13 19:26:11.944987
18	user@fiat.com	scrypt:32768:8:1$OmlUa8aqGVFKU1Nm$542cd6dbe9de191e4ca6081b6ddc048fa7ad450a75129fc1cd56a13dcdffdb0342b92777d10f5639028770a7323b1e5dad80d8ccf02483b023fc4d139473b50a	customer	5	2000	2026-07-13 19:26:22.490352
21	admin@utm.com	scrypt:32768:8:1$wNyChMNaHU4A7NCy$2842435cdd12e2cb18d4f6ebac3d333ee185f7da24735e37ce15889c11442098fda27e1ef46c3d2bea339ffb53a6e660f8db74fcf34f1f74f5294f62b383c6f0	company_admin	6	2000	2026-07-14 09:42:37.586896
22	user@utm.com	scrypt:32768:8:1$m6jrDnGXkultr2Hr$f00ae8ac3cf052ff9a1021d78b9407dd0ca82a672d8c6f411455aa03b09087a7d0feda62a01ee04f0023568f41514ab52d95809c7e2658dbd00fb90347d1687e	customer	6	1000	2026-07-14 09:42:37.691067
\.


--
-- Name: companies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: orange
--

SELECT pg_catalog.setval('public.companies_id_seq', 10, true);


--
-- Name: conversations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: orange
--

SELECT pg_catalog.setval('public.conversations_id_seq', 154, true);


--
-- Name: documents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: orange
--

SELECT pg_catalog.setval('public.documents_id_seq', 75, true);


--
-- Name: kb_deletions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: orange
--

SELECT pg_catalog.setval('public.kb_deletions_id_seq', 1, false);


--
-- Name: kb_ingestions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: orange
--

SELECT pg_catalog.setval('public.kb_ingestions_id_seq', 72, true);


--
-- Name: llm_providers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: orange
--

SELECT pg_catalog.setval('public.llm_providers_id_seq', 17, true);


--
-- Name: messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: orange
--

SELECT pg_catalog.setval('public.messages_id_seq', 304, true);


--
-- Name: pii_rules_id_seq; Type: SEQUENCE SET; Schema: public; Owner: orange
--

SELECT pg_catalog.setval('public.pii_rules_id_seq', 15, true);


--
-- Name: provider_call_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: orange
--

SELECT pg_catalog.setval('public.provider_call_log_id_seq', 389, true);


--
-- Name: staged_chunks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: orange
--

SELECT pg_catalog.setval('public.staged_chunks_id_seq', 3, true);


--
-- Name: token_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: orange
--

SELECT pg_catalog.setval('public.token_requests_id_seq', 4, true);


--
-- Name: token_usage_id_seq; Type: SEQUENCE SET; Schema: public; Owner: orange
--

SELECT pg_catalog.setval('public.token_usage_id_seq', 328, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: orange
--

SELECT pg_catalog.setval('public.users_id_seq', 28, true);


--
-- Name: companies companies_name_key; Type: CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_name_key UNIQUE (name);


--
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (id);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: kb_deletions kb_deletions_pkey; Type: CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.kb_deletions
    ADD CONSTRAINT kb_deletions_pkey PRIMARY KEY (id);


--
-- Name: kb_ingestions kb_ingestions_pkey; Type: CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.kb_ingestions
    ADD CONSTRAINT kb_ingestions_pkey PRIMARY KEY (id);


--
-- Name: llm_providers llm_providers_pkey; Type: CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.llm_providers
    ADD CONSTRAINT llm_providers_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: pii_rules pii_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.pii_rules
    ADD CONSTRAINT pii_rules_pkey PRIMARY KEY (id);


--
-- Name: provider_call_log provider_call_log_pkey; Type: CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.provider_call_log
    ADD CONSTRAINT provider_call_log_pkey PRIMARY KEY (id);


--
-- Name: staged_chunks staged_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.staged_chunks
    ADD CONSTRAINT staged_chunks_pkey PRIMARY KEY (id);


--
-- Name: token_requests token_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.token_requests
    ADD CONSTRAINT token_requests_pkey PRIMARY KEY (id);


--
-- Name: token_usage token_usage_pkey; Type: CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.token_usage
    ADD CONSTRAINT token_usage_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_companies_domain; Type: INDEX; Schema: public; Owner: orange
--

CREATE UNIQUE INDEX ix_companies_domain ON public.companies USING btree (domain);


--
-- Name: ix_conversations_company_id; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_conversations_company_id ON public.conversations USING btree (company_id);


--
-- Name: ix_documents_company_id; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_documents_company_id ON public.documents USING btree (company_id);


--
-- Name: ix_kb_deletions_company_id; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_kb_deletions_company_id ON public.kb_deletions USING btree (company_id);


--
-- Name: ix_kb_deletions_created_at; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_kb_deletions_created_at ON public.kb_deletions USING btree (created_at);


--
-- Name: ix_kb_ingestions_company_id; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_kb_ingestions_company_id ON public.kb_ingestions USING btree (company_id);


--
-- Name: ix_kb_ingestions_created_at; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_kb_ingestions_created_at ON public.kb_ingestions USING btree (created_at);


--
-- Name: ix_llm_providers_company_id; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_llm_providers_company_id ON public.llm_providers USING btree (company_id);


--
-- Name: ix_messages_conversation_id; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_messages_conversation_id ON public.messages USING btree (conversation_id);


--
-- Name: ix_provider_call_log_created_at; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_provider_call_log_created_at ON public.provider_call_log USING btree (created_at);


--
-- Name: ix_provider_call_log_provider_id; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_provider_call_log_provider_id ON public.provider_call_log USING btree (provider_id);


--
-- Name: ix_staged_chunks_company_id; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_staged_chunks_company_id ON public.staged_chunks USING btree (company_id);


--
-- Name: ix_staged_chunks_conversation_id; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_staged_chunks_conversation_id ON public.staged_chunks USING btree (conversation_id);


--
-- Name: ix_staged_chunks_created_at; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_staged_chunks_created_at ON public.staged_chunks USING btree (created_at);


--
-- Name: ix_staged_chunks_expires_at; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_staged_chunks_expires_at ON public.staged_chunks USING btree (expires_at);


--
-- Name: ix_token_requests_company_id; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_token_requests_company_id ON public.token_requests USING btree (company_id);


--
-- Name: ix_token_requests_created_at; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_token_requests_created_at ON public.token_requests USING btree (created_at);


--
-- Name: ix_token_requests_requester_id; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_token_requests_requester_id ON public.token_requests USING btree (requester_id);


--
-- Name: ix_token_requests_status; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_token_requests_status ON public.token_requests USING btree (status);


--
-- Name: ix_token_usage_company_id; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_token_usage_company_id ON public.token_usage USING btree (company_id);


--
-- Name: ix_token_usage_created_at; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_token_usage_created_at ON public.token_usage USING btree (created_at);


--
-- Name: ix_token_usage_provider_id; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_token_usage_provider_id ON public.token_usage USING btree (provider_id);


--
-- Name: ix_users_company_id; Type: INDEX; Schema: public; Owner: orange
--

CREATE INDEX ix_users_company_id ON public.users USING btree (company_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: orange
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: conversations conversations_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: conversations conversations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: documents documents_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: documents documents_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: kb_deletions kb_deletions_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.kb_deletions
    ADD CONSTRAINT kb_deletions_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: kb_deletions kb_deletions_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.kb_deletions
    ADD CONSTRAINT kb_deletions_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id);


--
-- Name: kb_deletions kb_deletions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.kb_deletions
    ADD CONSTRAINT kb_deletions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: kb_ingestions kb_ingestions_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.kb_ingestions
    ADD CONSTRAINT kb_ingestions_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: kb_ingestions kb_ingestions_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.kb_ingestions
    ADD CONSTRAINT kb_ingestions_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id);


--
-- Name: kb_ingestions kb_ingestions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.kb_ingestions
    ADD CONSTRAINT kb_ingestions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: llm_providers llm_providers_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.llm_providers
    ADD CONSTRAINT llm_providers_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: llm_providers llm_providers_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.llm_providers
    ADD CONSTRAINT llm_providers_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: messages messages_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id);


--
-- Name: pii_rules pii_rules_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.pii_rules
    ADD CONSTRAINT pii_rules_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: provider_call_log provider_call_log_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.provider_call_log
    ADD CONSTRAINT provider_call_log_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.llm_providers(id);


--
-- Name: staged_chunks staged_chunks_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.staged_chunks
    ADD CONSTRAINT staged_chunks_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: staged_chunks staged_chunks_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.staged_chunks
    ADD CONSTRAINT staged_chunks_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id);


--
-- Name: staged_chunks staged_chunks_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.staged_chunks
    ADD CONSTRAINT staged_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id);


--
-- Name: token_requests token_requests_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.token_requests
    ADD CONSTRAINT token_requests_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: token_requests token_requests_requester_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.token_requests
    ADD CONSTRAINT token_requests_requester_id_fkey FOREIGN KEY (requester_id) REFERENCES public.users(id);


--
-- Name: token_requests token_requests_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.token_requests
    ADD CONSTRAINT token_requests_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.users(id);


--
-- Name: token_usage token_usage_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.token_usage
    ADD CONSTRAINT token_usage_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: token_usage token_usage_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.token_usage
    ADD CONSTRAINT token_usage_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id);


--
-- Name: token_usage token_usage_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.token_usage
    ADD CONSTRAINT token_usage_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.llm_providers(id);


--
-- Name: token_usage token_usage_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.token_usage
    ADD CONSTRAINT token_usage_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: users users_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: orange
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- PostgreSQL database dump complete
--

\unrestrict DqhaZ6axAYYDMOIeZrjRZXhLNc3jkk48MG6N6PW2yUJDaytB97lCLfor0M0i8qs

