package com.lballoy.ledger;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.jdbc.autoconfigure.DataSourceAutoConfiguration;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;

@SpringBootApplication(exclude = {DataSourceAutoConfiguration.class })
public class LedgerApplication {
	
	@GET
	@Path("/")
	public String hello(){
		return "Hello!";
	}
	
	public static void main(String[] args) {
		SpringApplication.run(LedgerApplication.class, args);
	}
}
