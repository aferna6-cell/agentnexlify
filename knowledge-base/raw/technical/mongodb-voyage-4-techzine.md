---
source_url: https://www.techzine.eu/news/devops/137985/mongodb-launches-voyage-4-embedding-models-for-ai-apps/
fetched_at: 2026-04-13T22:12:56Z
category: technical
title: "MongoDB launches Voyage 4 embedding models for AI apps"
---

- 
 
- 
 
- 
 
- 
 
- 
 
- 
 
 
 
 
- 
 
- 

- 

- 

- 

- 
- 
- 
- 
- 

	
	MongoDB launches Voyage 4 embedding models for AI apps - Techzine Global
	
	
- 
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	

- 

- 

- 

- 

 

- 

- 

- 

- 

 

	
 	
		 
 
 
 	
 
 
 
 	
 
 

MongoDB is taking a new step toward AI developers with the general availability of the Voyage 4 embedding family and expansion of its startup program. The integration with Voyage AI, acquired last year, should make it easier for developers to take applications from prototype to production.

MongoDB is increasingly positioning itself as the foundation for AI stacks rather than just a database. “Customers increasingly do not think of MongoDB as just a database; they reframe the database as a foundation for their AI stack,” said Benjamin Flast, director of product management at MongoDB.

The embedding models are now available via APIs in the managed MongoDB Atlas service and in the on-premises community edition. Embeddings are numerical representations of data that capture semantic meaning as vectors. This allows systems to compare and retrieve information based on meaning rather than exact keywords.

## Four models for different scenarios

The Voyage 4 series consists of four variants, each with its own balance between accuracy, latency, and cost. The standard Voyage 4 model is intended for general use. Voyage 4 large offers the highest accuracy for information retrieval. Voyage 4 lite focuses on lower latency and cost. Finally, Voyage 4 nano is an open-weights model for local development and testing.

MongoDB says the models improve accuracy for production AI workloads. This is because data no longer needs to be moved or duplicated between separate systems. For developers, this means less complexity and faster implementation.

In addition, the company announced the general availability of voyage-multimodal-3.5. This model extends support for text and images to video. “This unlocks unified retrieval across multiple content types,” says Franklin Sun, staff product manager. “You have one embedding model instead of three to handle different data types.”

## Automatic embeddings and development tools

In public preview, MongoDB introduces automated embedding capabilities for MongoDB Community Vector Search. The feature automatically generates and stores embeddings when data is inserted, updated, or queried. Developers no longer need to manage separate embedding pipelines or external services.

Automatic embedding is available today for MongoDB Community Edition and will be coming soon to Atlas. MongoDB says the feature integrates with drivers and AI frameworks such as LangChain and LangGraph. Atlas users will also have access to embedding and reranking APIs that make Voyage AI models available directly within the platform.

An AI-powered assistant for MongoDB Compass and Atlas Data Explorer is now generally available. The assistant provides natural language guidance for common data operations such as query optimization and troubleshooting.

Tip: MongoDB launches its 5.1 version update
