package com.lballoy.ledger;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.jdbc.autoconfigure.DataSourceAutoConfiguration;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@SpringBootApplication(exclude = {DataSourceAutoConfiguration.class })
public class LedgerApplication {

	@RequestMapping("/")
	String home(){
		return "Hello World!";
	}

	@RequestMapping("/health")
	String get_heatlh(){
		return "Healthy!";
	}

	public static void main(String[] args) {
		SpringApplication.run(LedgerApplication.class, args);
	}

}
