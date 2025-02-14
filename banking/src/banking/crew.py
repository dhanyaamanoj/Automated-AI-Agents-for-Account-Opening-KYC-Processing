from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task


from banking.tools.fetch_acc_data import RequestDetailsTool
from banking.tools.data_extraction_tool import DocumentExtractionTool
from crewai.knowledge.source.pdf_knowledge_source import PDFKnowledgeSource
#from banking.tools.data_update import AccountNumberInsertTool



# Create a PDF knowledge source
pdf_source = PDFKnowledgeSource(file_paths=["/AOM.pdf"])
@CrewBase
class Banking:
    """Banking crew for KYC Verification & Onboarding"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def kyc_verification_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['kyc_verification_agent'],
            verbose=True
        )

    @agent
    def document_check__agent(self) -> Agent:
        return Agent(
            config=self.agents_config['document_check__agent'],
            max_itr= 1,
			verbose=True, pdf_knowledge_source=[pdf_source]
		)
    
    @agent
    def onboarding_agent(self) -> Agent:
        """Final Onboarding Agent to update customer details after verification."""
        return Agent(
            config=self.agents_config['onboarding_agent'],
            verbose=True,
            #tools=AccountNumberInsertTool
        )
  
    
    @task
    def fetch_acc_details_task(self) -> Task:
        return Task(
            config=self.tasks_config['fetch_acc_details_task'],
            tools=[RequestDetailsTool()],
            agent=self.kyc_verification_agent()
        )

    @task
    def kyc_verification_task(self) -> Task:
        return Task(
            config=self.tasks_config['kyc_verification_task'],
            tools=[DocumentExtractionTool()],  # Extracting data from documents
            agent=self.kyc_verification_agent(),
            context=[self.fetch_acc_details_task()]
        )

    @task
    def document_check_task(self) -> Task:
        return Task(
            config=self.tasks_config['document_check_task'],
            context=[self.kyc_verification_task()]  # Ensures onboarding happens after verification
            
        )
    @task
    def onboarding_task(self) -> Task:
        return Task(
			config=self.tasks_config['onboarding_task'],
			output_file='report.md'
		)


    @crew
    def crew(self) -> Crew:
        """Creates the Banking crew for KYC verification and onboarding"""

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
			pdf_knowledge_source=[pdf_source],
			verbose=True,
        )
